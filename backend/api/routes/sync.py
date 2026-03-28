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
    # Get user's outlet and brand context
    result = await db.execute(select(Outlet).filter(Outlet.id == current_user.outlet_id))
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
            await process_table_sync(db, OrderItem, request.changes.order_items, {}, server_hlc)
        if request.changes.payments:
            await process_table_sync(db, Payment, request.changes.payments, {"outlet_id": outlet_id}, server_hlc, conflict_strategy="financial_strict")
        if request.changes.shifts:
            await process_table_sync(db, Shift, request.changes.shifts, {"outlet_id": outlet_id}, server_hlc, conflict_strategy="financial_strict")
        if request.changes.cash_activities:
            await process_table_sync(db, CashActivity, request.changes.cash_activities, {}, server_hlc, conflict_strategy="financial_strict")
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
        outlet_stock=[]
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
    
    return SyncResponse(
        last_sync_hlc=server_hlc.to_string(),
        changes=pull_changes
    )
