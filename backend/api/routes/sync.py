import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, text
from datetime import datetime, timezone
from typing import Any, List, Dict, Optional
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
    # Resolve outlet dengan tenant-scoping validation (CRITICAL #3 fix).
    # Multi-outlet tenant tanpa outlet_id explicit = cross-outlet data leak risk.
    all_outlets = (await db.execute(
        select(Outlet).filter(
            Outlet.tenant_id == current_user.tenant_id,
            Outlet.deleted_at.is_(None),
        )
    )).scalars().all()
    if not all_outlets:
        raise HTTPException(status_code=400, detail="User is not assigned to an outlet")

    if request.outlet_id:
        # Explicit outlet_id di request — validate belongs to user's tenant
        outlet = next((o for o in all_outlets if str(o.id) == str(request.outlet_id)), None)
        if not outlet:
            raise HTTPException(
                status_code=403,
                detail="outlet_id tidak ditemukan atau bukan milik tenant Anda",
            )
    else:
        # Backward compat: auto-pick untuk single-outlet tenant saja.
        # Multi-outlet tenant WAJIB kirim outlet_id (cegah arbitrary .limit(1) leak).
        if len(all_outlets) > 1:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Tenant punya multiple outlet — outlet_id wajib di-set di "
                    "request body. Update Flutter client untuk kirim "
                    "SessionCache.outletId di payload."
                ),
            )
        outlet = all_outlets[0]

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

    # ─── Idempotency claim (CRITICAL #6 fix) ──────────────────────────────
    # Atomic INSERT ON CONFLICT — race-safe. Kalau RETURNING kosong = key udah
    # ada (claim by earlier/concurrent request) → skip push, biarin pull jalan
    # normal (stateless by last_sync_hlc). Kalau push nanti fail, TX rollback
    # = key hilang bareng push changes = retry boleh ulang. Zero ghost state.
    push_claimed = True
    if request.idempotency_key:
        try:
            claim_result = await db.execute(
                text(
                    "INSERT INTO sync_idempotency_keys (key, tenant_id, outlet_id) "
                    "VALUES (:key, :tid, :oid) ON CONFLICT DO NOTHING RETURNING key"
                ),
                {
                    "key": request.idempotency_key,
                    "tid": str(current_user.tenant_id),
                    "oid": str(outlet_id),
                },
            )
            push_claimed = claim_result.first() is not None
            if not push_claimed:
                logger.info(
                    "sync idempotency hit: tenant=%s outlet=%s key=%s — skipping push",
                    current_user.tenant_id, outlet_id, request.idempotency_key,
                )
        except Exception as e:
            # Fail-open: log + proses tetap (kalau table belum migrasi atau DB hiccup)
            logger.warning(
                "sync idempotency claim failed, proceeding without dedup: %s", e
            )

    # 1. PUSH (Apply changes from client to server) — skip kalau:
    #    (a) idempotency dedup hit, atau
    #    (b) cursor_hlc set = pagination continuation (push udah di first page)
    is_pagination_continuation = bool(request.cursor_hlc)
    if is_pagination_continuation:
        logger.info(
            "sync pagination continuation (cursor=%s) — skip push, pull only",
            request.cursor_hlc[:30] if len(request.cursor_hlc) > 30 else request.cursor_hlc,
        )
    if request.changes and push_claimed and not is_pagination_continuation:
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
                # Order.status enum: pending|preparing|ready|served|completed|cancelled
                terminal_states = {"completed", "cancelled"}
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
                            product_name=product.name,
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

    # 2. PULL with CURSOR PAGINATION (CRITICAL #7).
    # Effective cursor priority: cursor_hlc (intra-session pagination) >
    # last_sync_hlc (first page marker). Zero data loss: filter > cursor
    # ASC sorted, limit+1 detect has_more.
    effective_hlc_str = request.cursor_hlc or request.last_sync_hlc
    client_last_sync_hlc = None
    if effective_hlc_str:
        try:
            client_last_sync_hlc = HLC.from_string(effective_hlc_str)
        except ValueError:
            pass  # Invalid HLC → pull dari awal

    page_limit = request.limit  # validated by schema (10-2000)
    cursor_last_id = request.cursor_last_id  # tie-break untuk duplicate tuples

    # Collect per-table (records, had_more) dari get_table_changes helper.
    # Non-helper tables (order_items, outlet_stock, recipes, recipe_ingredients,
    # cash_activities) akan di-handle dgn inline paginated query di bawah.
    cat_records, cat_more = await get_table_changes(db, Category, {"brand_id": brand_id}, client_last_sync_hlc, server_node_id, limit=page_limit, cursor_last_id=cursor_last_id)
    prod_records, prod_more = await get_table_changes(db, Product, {"brand_id": brand_id}, client_last_sync_hlc, server_node_id, limit=page_limit, cursor_last_id=cursor_last_id)
    ord_records, ord_more = await get_table_changes(db, Order, {"outlet_id": outlet_id}, client_last_sync_hlc, server_node_id, limit=page_limit, cursor_last_id=cursor_last_id)
    pay_records, pay_more = await get_table_changes(db, Payment, {"outlet_id": outlet_id}, client_last_sync_hlc, server_node_id, limit=page_limit, cursor_last_id=cursor_last_id)
    shift_records, shift_more = await get_table_changes(db, Shift, {"outlet_id": outlet_id}, client_last_sync_hlc, server_node_id, limit=page_limit, cursor_last_id=cursor_last_id)
    ing_records, ing_more = await get_table_changes(db, Ingredient, {"brand_id": brand_id}, client_last_sync_hlc, server_node_id, limit=page_limit, cursor_last_id=cursor_last_id)

    pull_changes = SyncPayload(
        categories=cat_records,
        products=prod_records,
        orders=ord_records,
        order_items=[],
        payments=pay_records,
        shifts=shift_records,
        cash_activities=[],
        outlet_stock=[],
        ingredients=ing_records,
        recipes=[],
        recipe_ingredients=[]
    )

    # Aggregate has_more tracker — any table filled limit = page berikutnya ada
    has_more_any = cat_more or prod_more or ord_more or pay_more or shift_more or ing_more
    
    # Helper inline — build record dict + attach HLC. Dipakai oleh custom
    # paginated queries di bawah (order_items, outlet_stock, recipes,
    # recipe_ingredients, cash_activities) yang pake JOIN jadi gak fit
    # get_table_changes generic helper.
    from backend.services.sync import _SYNC_SKIP_COLUMNS
    def _row_to_dict(r, has_row_version: bool = True):
        d = {}
        for c in r.__table__.columns:
            if c.name in _SYNC_SKIP_COLUMNS:
                continue
            val = getattr(r, c.name)
            if isinstance(val, datetime):
                d[c.name] = val.isoformat()
            elif isinstance(val, uuid.UUID):
                d[c.name] = str(val)
            elif hasattr(val, "tolist") and callable(val.tolist):
                d[c.name] = val.tolist()
            elif hasattr(val, "item") and callable(val.item) and type(val).__module__ == "numpy":
                d[c.name] = val.item()
            else:
                d[c.name] = val
        d["is_deleted"] = getattr(r, "deleted_at", None) is not None
        r_updated_at = getattr(r, "updated_at")
        if r_updated_at.tzinfo is None:
            r_updated_at = r_updated_at.replace(tzinfo=timezone.utc)
        r_timestamp = int(r_updated_at.timestamp() * 1000)
        r_counter = getattr(r, "row_version", 0) if has_row_version else 0
        d["hlc"] = HLC(timestamp=r_timestamp, counter=r_counter, node_id=server_node_id).to_string()
        return d

    def _apply_delta_filter(stmt_in, model_class):
        """Apply (updated_at, row_version, id) > cursor — identical semantic
        dgn get_table_changes helper. Range boundary utk HLC ms vs DB µs
        precision + id tie-break utk duplicate (ts, rv) rows."""
        if not (client_last_sync_hlc and client_last_sync_hlc.timestamp > 0):
            return stmt_in
        from datetime import timedelta
        last_sync_dt = datetime.fromtimestamp(client_last_sync_hlc.timestamp / 1000.0, tz=timezone.utc)
        ms_end = last_sync_dt + timedelta(microseconds=999)
        last_counter = client_last_sync_hlc.counter
        if hasattr(model_class, "row_version"):
            conds = [
                model_class.updated_at > ms_end,
                and_(
                    model_class.updated_at >= last_sync_dt,
                    model_class.updated_at <= ms_end,
                    model_class.row_version > last_counter,
                ),
            ]
            if cursor_last_id and hasattr(model_class, "id"):
                conds.append(
                    and_(
                        model_class.updated_at >= last_sync_dt,
                        model_class.updated_at <= ms_end,
                        model_class.row_version == last_counter,
                        model_class.id > uuid.UUID(cursor_last_id),
                    )
                )
            return stmt_in.filter(or_(*conds))
        return stmt_in.filter(model_class.updated_at >= last_sync_dt)

    # Custom pull for order_items — JOIN Order untuk outlet scoping.
    # Pagination: ORDER BY + LIMIT+1 pattern.
    stmt = select(OrderItem).join(Order).filter(Order.outlet_id == outlet_id)
    stmt = _apply_delta_filter(stmt, OrderItem)
    stmt = stmt.order_by(OrderItem.updated_at.asc(), OrderItem.row_version.asc(), OrderItem.id.asc()).limit(page_limit + 1)
    order_items_records = (await db.execute(stmt)).scalars().all()
    oi_more = len(order_items_records) > page_limit
    if oi_more:
        order_items_records = order_items_records[:page_limit]
    pull_changes.order_items = [_row_to_dict(r) for r in order_items_records]
    has_more_any = has_more_any or oi_more

    # Custom pull for outlet_stock
    from backend.models.product import OutletStock
    stmt = select(OutletStock).filter(OutletStock.outlet_id == outlet_id)
    stmt = _apply_delta_filter(stmt, OutletStock)
    stmt = stmt.order_by(OutletStock.updated_at.asc(), OutletStock.row_version.asc(), OutletStock.id.asc()).limit(page_limit + 1)
    stock_records = (await db.execute(stmt)).scalars().all()
    stock_more = len(stock_records) > page_limit
    if stock_more:
        stock_records = stock_records[:page_limit]
    pull_changes.outlet_stock = [_row_to_dict(r) for r in stock_records]
    has_more_any = has_more_any or stock_more
    
    # Custom pull for recipes (no row_version — filter via product.brand_id)
    stmt_recipe = select(Recipe).join(Product).filter(Product.brand_id == brand_id)
    if client_last_sync_hlc and client_last_sync_hlc.timestamp > 0:
        last_sync_dt = datetime.fromtimestamp(client_last_sync_hlc.timestamp / 1000.0, tz=timezone.utc)
        stmt_recipe = stmt_recipe.filter(Recipe.updated_at >= last_sync_dt)
    stmt_recipe = stmt_recipe.order_by(Recipe.updated_at.asc()).limit(page_limit + 1)
    recipe_records = (await db.execute(stmt_recipe)).scalars().all()
    recipe_more = len(recipe_records) > page_limit
    if recipe_more:
        recipe_records = recipe_records[:page_limit]
    pull_changes.recipes = [_row_to_dict(r, has_row_version=False) for r in recipe_records]
    has_more_any = has_more_any or recipe_more

    # Custom pull for recipe_ingredients (join via recipe→product.brand_id)
    stmt_ri = select(RecipeIngredient).join(Recipe).join(Product).filter(Product.brand_id == brand_id)
    if client_last_sync_hlc and client_last_sync_hlc.timestamp > 0:
        last_sync_dt = datetime.fromtimestamp(client_last_sync_hlc.timestamp / 1000.0, tz=timezone.utc)
        stmt_ri = stmt_ri.filter(RecipeIngredient.updated_at >= last_sync_dt)
    stmt_ri = stmt_ri.order_by(RecipeIngredient.updated_at.asc()).limit(page_limit + 1)
    ri_records = (await db.execute(stmt_ri)).scalars().all()
    ri_more = len(ri_records) > page_limit
    if ri_more:
        ri_records = ri_records[:page_limit]
    pull_changes.recipe_ingredients = [_row_to_dict(r, has_row_version=False) for r in ri_records]
    has_more_any = has_more_any or ri_more

    # Custom pull for cash_activities (join Shift untuk outlet scoping)
    stmt = select(CashActivity).join(Shift).filter(Shift.outlet_id == outlet_id)
    stmt = _apply_delta_filter(stmt, CashActivity)
    stmt = stmt.order_by(CashActivity.updated_at.asc(), CashActivity.row_version.asc(), CashActivity.id.asc()).limit(page_limit + 1)
    ca_records = (await db.execute(stmt)).scalars().all()
    ca_more = len(ca_records) > page_limit
    if ca_more:
        ca_records = ca_records[:page_limit]
    pull_changes.cash_activities = [_row_to_dict(r) for r in ca_records]
    has_more_any = has_more_any or ca_more
    
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

    # Compute next_cursor_hlc + next_cursor_last_id = record dgn HLC tertinggi
    # di batch. Client kirim balik duanya untuk next page (unique tie-break).
    next_cursor_hlc_str: Optional[str] = None
    next_cursor_last_id_str: Optional[str] = None
    if has_more_any:
        best_record = None  # (hlc_tuple, id, hlc_str)
        for records_list in (
            pull_changes.categories, pull_changes.products, pull_changes.orders,
            pull_changes.order_items, pull_changes.payments, pull_changes.shifts,
            pull_changes.cash_activities, pull_changes.outlet_stock,
            pull_changes.ingredients, pull_changes.recipes,
            pull_changes.recipe_ingredients,
        ):
            for rec in records_list:
                hlc_v = rec.get("hlc")
                rec_id = rec.get("id")
                if not hlc_v:
                    continue
                try:
                    h = HLC.from_string(hlc_v)
                except Exception:
                    continue
                key = (h.timestamp, h.counter, rec_id or "")
                if best_record is None or key > best_record[0]:
                    best_record = (key, rec_id, hlc_v)
        if best_record is not None:
            next_cursor_hlc_str = best_record[2]
            next_cursor_last_id_str = best_record[1]

    # Observability #10: emit sync volume metrics per-table.
    try:
        from backend.core.metrics import observe_sync_volume
        for table_name, records in (
            ("categories", pull_changes.categories),
            ("products", pull_changes.products),
            ("orders", pull_changes.orders),
            ("order_items", pull_changes.order_items),
            ("payments", pull_changes.payments),
            ("shifts", pull_changes.shifts),
            ("cash_activities", pull_changes.cash_activities),
            ("outlet_stock", pull_changes.outlet_stock),
            ("ingredients", pull_changes.ingredients),
            ("recipes", pull_changes.recipes),
            ("recipe_ingredients", pull_changes.recipe_ingredients),
        ):
            observe_sync_volume(table_name, "pull", len(records))
        # Push volume (client → server changes count)
        if request.changes:
            for table_name, records in (
                ("categories", request.changes.categories),
                ("products", request.changes.products),
                ("orders", request.changes.orders),
                ("order_items", request.changes.order_items),
                ("payments", request.changes.payments),
                ("shifts", request.changes.shifts),
                ("cash_activities", request.changes.cash_activities),
                ("outlet_stock", request.changes.outlet_stock),
            ):
                observe_sync_volume(table_name, "push", len(records))
    except Exception:
        # Metrics tidak boleh break business logic
        pass

    return SyncResponse(
        last_sync_hlc=server_hlc.to_string(),
        changes=pull_changes,
        stock_mode=sm_str,
        subscription_tier=sub_tier,
        has_more=has_more_any,
        next_cursor_hlc=next_cursor_hlc_str,
        next_cursor_last_id=next_cursor_last_id_str,
    )
