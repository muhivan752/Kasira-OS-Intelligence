import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from datetime import datetime, timezone
from typing import Any, List, Dict
import uuid

from backend.api import deps
from backend.schemas.sync import SyncRequest, SyncResponse, SyncPayload
from backend.models.user import User
from backend.models.category import Category
from backend.models.product import Product
from backend.models.order import Order, OrderItem
from backend.models.payment import Payment
from backend.models.outlet import Outlet
from backend.models.shift import Shift, CashActivity
from backend.services.sync import process_table_sync, process_stock_sync, get_table_changes, utc_now
from backend.services.crdt import HLC
from backend.services.stock_service import deduct_stock as svc_deduct_stock
from backend.services.ingredient_stock_service import deduct_ingredients_for_product as svc_deduct_ingredients
from backend.models.tenant import Tenant
from backend.models.ingredient import Ingredient
from backend.models.recipe import Recipe, RecipeIngredient

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=SyncResponse)
async def sync_data(
    request: SyncRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """
    Pure CRDT Sync Engine Endpoint (Pull & Push)
    """
    # Get user's outlet via tenant_id (User model has no outlet_id column)
    result = await db.execute(
        select(Outlet).filter(
            Outlet.tenant_id == current_user.tenant_id,
            Outlet.deleted_at.is_(None),
        ).limit(1)
    )
    outlet = result.scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=400, detail="User is not assigned to an outlet")
        
    brand_id = outlet.brand_id
    outlet_id = outlet.id
    
    # Validate and enforce node_id format
    if not request.node_id or ":" not in request.node_id:
        # If client didn't send proper node_id, we enforce a default one for this session
        client_node_id = f"{outlet_id}:unknown_device"
    else:
        client_node_id = request.node_id
        
    # Initialize Server HLC
    server_node_id = f"server:{outlet_id}"
    server_hlc = HLC.generate(node_id=server_node_id)
    
    # 1. PUSH (Apply changes from client to server)
    if request.changes:
        if request.changes.categories:
            await process_table_sync(db, Category, request.changes.categories, {"brand_id": brand_id}, server_hlc)
        if request.changes.products:
            await process_table_sync(db, Product, request.changes.products, {"brand_id": brand_id}, server_hlc)
        if request.changes.orders:
            await process_table_sync(db, Order, request.changes.orders, {"outlet_id": outlet_id}, server_hlc, conflict_strategy="financial_strict")
        if request.changes.order_items:
            # 🔒 Tenant isolation + terminal-state guard (cegah cross-tenant write + ghost discount)
            # Client bisa aja push OrderItem dengan UUID sembarang. Kita WAJIB verify:
            #   1. Parent Order.outlet_id == outlet_id (tenant check)
            #   2. Parent Order bukan dalam state terminal (paid/completed/refunded/cancelled)
            # Kalau parent belum ada di DB (new order di batch yang sama), cek batch orders juga.
            item_order_ids = [oi.get("order_id") for oi in request.changes.order_items if oi.get("order_id")]
            trusted_order_items = []
            if item_order_ids:
                parent_rows = (await db.execute(
                    select(Order.id, Order.status, Order.outlet_id).where(Order.id.in_(item_order_ids))
                )).all()
                parent_map = {}
                for pid, pstatus, poutlet in parent_rows:
                    status_str = pstatus.value if hasattr(pstatus, 'value') else str(pstatus)
                    parent_map[str(pid)] = (status_str, str(poutlet))
                batch_order_ids = {str(o.get("id")) for o in (request.changes.orders or []) if o.get("id")}
                terminal_states = {"paid", "completed", "refunded", "cancelled"}
                for oi in request.changes.order_items:
                    oid = str(oi.get("order_id") or "")
                    if oid in parent_map:
                        pstatus, poutlet = parent_map[oid]
                        if poutlet != str(outlet_id):
                            logger.warning("sync: reject cross-tenant order_item order_id=%s", oid)
                            continue
                        if pstatus in terminal_states:
                            logger.warning("sync: reject order_item on terminal order_id=%s status=%s", oid, pstatus)
                            continue
                        trusted_order_items.append(oi)
                    elif oid in batch_order_ids:
                        # Parent ikut di-push di batch yang sama — orders.push flushed duluan, jadi
                        # kalau gak ketemu di parent_map artinya orders.push juga di-reject/filter.
                        # Aman: skip defensif.
                        logger.warning("sync: reject order_item with batch-parent order_id=%s (parent filtered)", oid)
                        continue
                    else:
                        logger.warning("sync: reject order_item unknown parent order_id=%s", oid)

            await process_table_sync(db, OrderItem, trusted_order_items, {}, server_hlc, conflict_strategy="financial_strict")
            # Trigger stock deduction untuk order items yang baru sync dari offline
            # Idempotent — stock_service._is_sale_already_recorded + ingredient_stock_service
            # event-log check cegah double-deduct saat retry.
            tenant_res = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
            tenant = tenant_res.scalar_one_or_none()
            raw_tier = getattr(tenant, "subscription_tier", "starter") or "starter" if tenant else "starter"
            tier = raw_tier.value if hasattr(raw_tier, 'value') else str(raw_tier)

            sm = getattr(outlet, 'stock_mode', 'simple')
            stock_mode = sm.value if hasattr(sm, 'value') else str(sm or 'simple')

            for item_data in trusted_order_items:
                product = await db.get(Product, item_data.get("product_id"))
                if not (product and product.stock_enabled):
                    continue
                order_id_val = item_data.get("order_id")
                qty_val = item_data.get("quantity", 1)
                try:
                    if stock_mode == 'recipe':
                        await svc_deduct_ingredients(
                            db,
                            product_id=product.id,
                            quantity=qty_val,
                            outlet_id=outlet_id,
                            order_id=order_id_val,
                            user_id=current_user.id,
                            tier=tier,
                        )
                    else:
                        await svc_deduct_stock(
                            db,
                            product=product,
                            quantity=qty_val,
                            outlet_id=outlet_id,
                            order_id=order_id_val,
                            user_id=current_user.id,
                            tier=tier,
                        )
                except HTTPException as e:
                    # Insufficient stock saat offline order overshoot — log & lanjut
                    # supaya sync gak gagal total karena 1 item bermasalah.
                    logger.warning(
                        "sync stock deduct skipped product=%s order=%s: %s",
                        product.id, order_id_val, e.detail,
                    )
                except Exception:
                    logger.exception(
                        "sync stock deduct failed product=%s order=%s",
                        product.id, order_id_val,
                    )
        if request.changes.payments:
            await process_table_sync(db, Payment, request.changes.payments, {"outlet_id": outlet_id}, server_hlc, conflict_strategy="financial_strict")
        if request.changes.shifts:
            await process_table_sync(db, Shift, request.changes.shifts, {"outlet_id": outlet_id}, server_hlc, conflict_strategy="financial_strict")
        if request.changes.cash_activities:
            # 🔒 Tenant isolation: CashActivity terhubung ke Shift via shift_id.
            # Hanya terima CA yang shift-nya milik outlet ini.
            ca_shift_ids = [ca.get("shift_id") for ca in request.changes.cash_activities if ca.get("shift_id")]
            trusted_ca = []
            if ca_shift_ids:
                valid_shifts = (await db.execute(
                    select(Shift.id).where(
                        Shift.id.in_(ca_shift_ids),
                        Shift.outlet_id == outlet_id,
                    )
                )).scalars().all()
                valid_shift_ids = {str(sid) for sid in valid_shifts}
                batch_shift_ids = {str(s.get("id")) for s in (request.changes.shifts or []) if s.get("id")}
                for ca in request.changes.cash_activities:
                    sid = str(ca.get("shift_id") or "")
                    if sid in valid_shift_ids:
                        trusted_ca.append(ca)
                    elif sid in batch_shift_ids:
                        logger.warning("sync: reject cash_activity with batch-parent shift=%s (filtered)", sid)
                    else:
                        logger.warning("sync: reject cash_activity unknown/cross-tenant shift=%s", sid)
            await process_table_sync(db, CashActivity, trusted_ca, {}, server_hlc, conflict_strategy="financial_strict")
        if request.changes.outlet_stock:
            await process_stock_sync(db, request.changes.outlet_stock, outlet_id, server_hlc)
            
        # Commit all pushed changes in a single transaction
        await db.commit()
            
    # 2. PULL (Get changes from server to client since last_sync_hlc)
    client_last_sync_hlc = None
    if request.last_sync_hlc:
        try:
            client_last_sync_hlc = HLC.from_string(request.last_sync_hlc)
        except ValueError:
            pass # Invalid HLC string, pull everything
            
    pull_changes = SyncPayload(
        categories=await get_table_changes(db, Category, {"brand_id": brand_id}, client_last_sync_hlc, server_node_id),
        products=await get_table_changes(db, Product, {"brand_id": brand_id}, client_last_sync_hlc, server_node_id),
        orders=await get_table_changes(db, Order, {"outlet_id": outlet_id}, client_last_sync_hlc, server_node_id),
        order_items=[],
        payments=await get_table_changes(db, Payment, {"outlet_id": outlet_id}, client_last_sync_hlc, server_node_id),
        shifts=await get_table_changes(db, Shift, {"outlet_id": outlet_id}, client_last_sync_hlc, server_node_id),
        cash_activities=[],
        outlet_stock=[],
        ingredients=await get_table_changes(db, Ingredient, {"brand_id": brand_id}, client_last_sync_hlc, server_node_id),
        recipes=[],
        recipe_ingredients=[]
    )
    
    # Custom pull for order_items
    stmt = select(OrderItem).join(Order).filter(Order.outlet_id == outlet_id)
    if client_last_sync_hlc and client_last_sync_hlc.timestamp > 0:
        last_sync_dt = datetime.fromtimestamp(client_last_sync_hlc.timestamp / 1000.0, tz=timezone.utc)
        last_counter = client_last_sync_hlc.counter
        stmt = stmt.filter(
            or_(
                OrderItem.updated_at > last_sync_dt,
                and_(
                    OrderItem.updated_at == last_sync_dt,
                    OrderItem.row_version > last_counter
                )
            )
        )
        
    result = await db.execute(stmt)
    order_items_records = result.scalars().all()
    
    oi_result = []
    for r in order_items_records:
        record_dict = {}
        for c in r.__table__.columns:
            val = getattr(r, c.name)
            if isinstance(val, datetime):
                record_dict[c.name] = val.isoformat()
            elif isinstance(val, uuid.UUID):
                record_dict[c.name] = str(val)
            else:
                record_dict[c.name] = val
                
        record_dict["is_deleted"] = getattr(r, "deleted_at", None) is not None
                
        r_updated_at = getattr(r, "updated_at")
        if r_updated_at.tzinfo is None:
            r_updated_at = r_updated_at.replace(tzinfo=timezone.utc)
        r_timestamp = int(r_updated_at.timestamp() * 1000)
        r_counter = getattr(r, "row_version", 0)
        r_hlc = HLC(timestamp=r_timestamp, counter=r_counter, node_id=server_node_id)
        record_dict["hlc"] = r_hlc.to_string()
        oi_result.append(record_dict)
        
    pull_changes.order_items = oi_result
    
    # Custom pull for outlet_stock
    from backend.models.product import OutletStock
    stmt = select(OutletStock).filter(OutletStock.outlet_id == outlet_id)
    if client_last_sync_hlc and client_last_sync_hlc.timestamp > 0:
        last_sync_dt = datetime.fromtimestamp(client_last_sync_hlc.timestamp / 1000.0, tz=timezone.utc)
        last_counter = client_last_sync_hlc.counter
        stmt = stmt.filter(
            or_(
                OutletStock.updated_at > last_sync_dt,
                and_(
                    OutletStock.updated_at == last_sync_dt,
                    OutletStock.row_version > last_counter
                )
            )
        )
        
    result = await db.execute(stmt)
    stock_records = result.scalars().all()
    
    stock_result = []
    for r in stock_records:
        record_dict = {}
        for c in r.__table__.columns:
            val = getattr(r, c.name)
            if isinstance(val, datetime):
                record_dict[c.name] = val.isoformat()
            elif isinstance(val, uuid.UUID):
                record_dict[c.name] = str(val)
            else:
                record_dict[c.name] = val
                
        record_dict["is_deleted"] = getattr(r, "deleted_at", None) is not None
                
        r_updated_at = getattr(r, "updated_at")
        if r_updated_at.tzinfo is None:
            r_updated_at = r_updated_at.replace(tzinfo=timezone.utc)
        r_timestamp = int(r_updated_at.timestamp() * 1000)
        r_counter = getattr(r, "row_version", 0)
        r_hlc = HLC(timestamp=r_timestamp, counter=r_counter, node_id=server_node_id)
        record_dict["hlc"] = r_hlc.to_string()
        stock_result.append(record_dict)
        
    pull_changes.outlet_stock = stock_result
    
    # Custom pull for recipes (read-only, no row_version — filter via product.brand_id)
    stmt_recipe = select(Recipe).join(Product).filter(Product.brand_id == brand_id)
    if client_last_sync_hlc and client_last_sync_hlc.timestamp > 0:
        last_sync_dt = datetime.fromtimestamp(client_last_sync_hlc.timestamp / 1000.0, tz=timezone.utc)
        stmt_recipe = stmt_recipe.filter(Recipe.updated_at >= last_sync_dt)
    result = await db.execute(stmt_recipe)
    recipe_records = result.scalars().all()
    recipe_result = []
    for r in recipe_records:
        record_dict = {}
        for c in r.__table__.columns:
            val = getattr(r, c.name)
            if isinstance(val, datetime):
                record_dict[c.name] = val.isoformat()
            elif isinstance(val, uuid.UUID):
                record_dict[c.name] = str(val)
            else:
                record_dict[c.name] = val
        record_dict["is_deleted"] = getattr(r, "deleted_at", None) is not None
        r_updated_at = getattr(r, "updated_at")
        if r_updated_at.tzinfo is None:
            r_updated_at = r_updated_at.replace(tzinfo=timezone.utc)
        r_timestamp = int(r_updated_at.timestamp() * 1000)
        r_hlc = HLC(timestamp=r_timestamp, counter=0, node_id=server_node_id)
        record_dict["hlc"] = r_hlc.to_string()
        recipe_result.append(record_dict)
    pull_changes.recipes = recipe_result

    # Custom pull for recipe_ingredients (join via recipe→product.brand_id)
    stmt_ri = select(RecipeIngredient).join(Recipe).join(Product).filter(Product.brand_id == brand_id)
    if client_last_sync_hlc and client_last_sync_hlc.timestamp > 0:
        last_sync_dt = datetime.fromtimestamp(client_last_sync_hlc.timestamp / 1000.0, tz=timezone.utc)
        stmt_ri = stmt_ri.filter(RecipeIngredient.updated_at >= last_sync_dt)
    result = await db.execute(stmt_ri)
    ri_records = result.scalars().all()
    ri_result = []
    for r in ri_records:
        record_dict = {}
        for c in r.__table__.columns:
            val = getattr(r, c.name)
            if isinstance(val, datetime):
                record_dict[c.name] = val.isoformat()
            elif isinstance(val, uuid.UUID):
                record_dict[c.name] = str(val)
            else:
                record_dict[c.name] = val
        record_dict["is_deleted"] = getattr(r, "deleted_at", None) is not None
        r_updated_at = getattr(r, "updated_at")
        if r_updated_at.tzinfo is None:
            r_updated_at = r_updated_at.replace(tzinfo=timezone.utc)
        r_timestamp = int(r_updated_at.timestamp() * 1000)
        r_hlc = HLC(timestamp=r_timestamp, counter=0, node_id=server_node_id)
        record_dict["hlc"] = r_hlc.to_string()
        ri_result.append(record_dict)
    pull_changes.recipe_ingredients = ri_result

    # Custom pull for cash_activities
    stmt = select(CashActivity).join(Shift).filter(Shift.outlet_id == outlet_id)
    if client_last_sync_hlc and client_last_sync_hlc.timestamp > 0:
        last_sync_dt = datetime.fromtimestamp(client_last_sync_hlc.timestamp / 1000.0, tz=timezone.utc)
        last_counter = client_last_sync_hlc.counter
        stmt = stmt.filter(
            or_(
                CashActivity.updated_at > last_sync_dt,
                and_(
                    CashActivity.updated_at == last_sync_dt,
                    CashActivity.row_version > last_counter
                )
            )
        )
        
    result = await db.execute(stmt)
    ca_records = result.scalars().all()
    
    ca_result = []
    for r in ca_records:
        record_dict = {}
        for c in r.__table__.columns:
            val = getattr(r, c.name)
            if isinstance(val, datetime):
                record_dict[c.name] = val.isoformat()
            elif isinstance(val, uuid.UUID):
                record_dict[c.name] = str(val)
            else:
                record_dict[c.name] = val
                
        record_dict["is_deleted"] = getattr(r, "deleted_at", None) is not None
                
        r_updated_at = getattr(r, "updated_at")
        if r_updated_at.tzinfo is None:
            r_updated_at = r_updated_at.replace(tzinfo=timezone.utc)
        r_timestamp = int(r_updated_at.timestamp() * 1000)
        r_counter = getattr(r, "row_version", 0)
        r_hlc = HLC(timestamp=r_timestamp, counter=r_counter, node_id=server_node_id)
        record_dict["hlc"] = r_hlc.to_string()
        ca_result.append(record_dict)
        
    pull_changes.cash_activities = ca_result
    
    # Include stock_mode + subscription_tier so Flutter stays in sync
    sm = getattr(outlet, 'stock_mode', 'simple')
    sm_str = sm.value if hasattr(sm, 'value') else str(sm or 'simple')

    sub_tier = "starter"
    sync_tenant = (await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )).scalar_one_or_none()
    if sync_tenant:
        st = getattr(sync_tenant, 'subscription_tier', 'starter')
        sub_tier = st.value if hasattr(st, 'value') else str(st or 'starter')

    return SyncResponse(
        last_sync_hlc=server_hlc.to_string(),
        changes=pull_changes,
        stock_mode=sm_str,
        subscription_tier=sub_tier,
    )
