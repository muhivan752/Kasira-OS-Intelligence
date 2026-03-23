from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from datetime import datetime, timezone
from typing import Any, List, Dict
import uuid

from backend.models.category import Category
from backend.models.product import Product
from backend.models.order import Order, OrderItem
from backend.models.payment import Payment
from backend.schemas.sync import SyncPayload
from backend.services.crdt import HLC, PNCounter

def utc_now():
    return datetime.now(timezone.utc)

async def process_table_sync(db: AsyncSession, model_class, client_records: List[Dict[str, Any]], filter_kwargs: dict, server_hlc: HLC, conflict_strategy: str = "hlc_lww"):
    """
    Pure CRDT Sync logic for a table using HLC and row_version.
    """
    for record in client_records:
        record_id = record.get("id")
        if not record_id:
            continue
            
        # Parse client HLC
        client_hlc_str = record.get("hlc")
        if not client_hlc_str:
            # Fallback if client doesn't send HLC
            client_hlc = HLC.generate(node_id="client_unknown")
        else:
            client_hlc = HLC.from_string(client_hlc_str)
            
        # Update server HLC based on received client HLC
        server_hlc.receive(client_hlc)
                
        # Query existing record
        stmt = select(model_class).filter(model_class.id == record_id)
        for k, v in filter_kwargs.items():
            stmt = stmt.filter(getattr(model_class, k) == v)
            
        result = await db.execute(stmt)
        db_record = result.scalar_one_or_none()
        
        if db_record:
            # Financial Strict Strategy: Server wins if status is final
            if conflict_strategy == "financial_strict" and hasattr(db_record, "status"):
                if db_record.status in ["paid", "completed", "refunded", "cancelled"]:
                    continue # Skip update, server wins
            
            # Optimistic Locking & CRDT Conflict Resolution
            # We use row_version to track changes. If the client sends a row_version,
            # we can use it to detect conflicts. But with HLC, we compare causality.
            
            # Since we don't store HLC per row yet, we simulate it using updated_at and row_version
            # For a true CRDT, we should trust the HLC. If client HLC > server's last known state, client wins.
            # We will use updated_at as the timestamp part of the server's HLC for this row.
            db_updated_at = db_record.updated_at
            if db_updated_at.tzinfo is None:
                db_updated_at = db_updated_at.replace(tzinfo=timezone.utc)
            
            db_timestamp = int(db_updated_at.timestamp() * 1000)
            db_counter = getattr(db_record, "row_version", 0)
            db_hlc = HLC(timestamp=db_timestamp, counter=db_counter, node_id=server_hlc.node_id)
            
            if client_hlc.compare(db_hlc) > 0:
                # Client wins
                for key, value in record.items():
                    if hasattr(db_record, key) and key not in ["created_at", "updated_at", "row_version", "hlc"]:
                        setattr(db_record, key, value)
                
                # Update timestamp and increment row_version
                db_record.updated_at = utc_now()
                if hasattr(db_record, "row_version"):
                    db_record.row_version += 1
        else:
            # Insert new record
            for k, v in filter_kwargs.items():
                record[k] = v
                
            # Remove keys that don't exist in model
            valid_keys = {c.name for c in model_class.__table__.columns}
            clean_record = {k: v for k, v in record.items() if k in valid_keys}
            
            new_record = model_class(**clean_record)
            if hasattr(new_record, "row_version"):
                new_record.row_version = 1
            db.add(new_record)
            
    await db.commit()

async def process_stock_sync(db: AsyncSession, client_records: List[Dict[str, Any]], outlet_id: uuid.UUID, server_hlc: HLC):
    """
    Process PN-Counter sync for outlet_stock.
    """
    from backend.models.product import OutletStock
    
    for record in client_records:
        product_id = record.get("product_id")
        if not product_id:
            continue
            
        client_hlc_str = record.get("hlc")
        if client_hlc_str:
            client_hlc = HLC.from_string(client_hlc_str)
            server_hlc.receive(client_hlc)
            
        client_p = record.get("crdt_positive", {})
        client_n = record.get("crdt_negative", {})
        
        stmt = select(OutletStock).filter(
            OutletStock.product_id == product_id,
            OutletStock.outlet_id == outlet_id
        )
        result = await db.execute(stmt)
        db_record = result.scalar_one_or_none()
        
        if db_record:
            # Merge PN-Counters
            merged_p = PNCounter.merge(db_record.crdt_positive or {}, client_p)
            merged_n = PNCounter.merge(db_record.crdt_negative or {}, client_n)
            
            db_record.crdt_positive = merged_p
            db_record.crdt_negative = merged_n
            # Guard against negative computed_stock
            db_record.computed_stock = max(0, PNCounter.get_value(merged_p, merged_n))
            
            db_record.updated_at = utc_now()
            if hasattr(db_record, "row_version"):
                db_record.row_version += 1
        else:
            # Insert new stock record
            new_record = OutletStock(
                id=uuid.uuid4(),
                outlet_id=outlet_id,
                product_id=product_id,
                crdt_positive=client_p,
                crdt_negative=client_n,
                # Guard against negative computed_stock
                computed_stock=max(0, PNCounter.get_value(client_p, client_n)),
                row_version=1
            )
            db.add(new_record)
            
    await db.commit()

async def get_table_changes(db: AsyncSession, model_class, filter_kwargs: dict, last_sync_hlc: HLC, server_node_id: str) -> List[Dict[str, Any]]:
    stmt = select(model_class)
    for k, v in filter_kwargs.items():
        stmt = stmt.filter(getattr(model_class, k) == v)
        
    if last_sync_hlc and last_sync_hlc.timestamp > 0:
        # Convert HLC timestamp back to datetime for querying
        last_sync_dt = datetime.fromtimestamp(last_sync_hlc.timestamp / 1000.0, tz=timezone.utc)
        last_counter = last_sync_hlc.counter
        
        if hasattr(model_class, "row_version"):
            stmt = stmt.filter(
                or_(
                    model_class.updated_at > last_sync_dt,
                    and_(
                        model_class.updated_at == last_sync_dt,
                        model_class.row_version > last_counter
                    )
                )
            )
        else:
            stmt = stmt.filter(model_class.updated_at >= last_sync_dt)
        
    result = await db.execute(stmt)
    records = result.scalars().all()
    
    result_list = []
    for r in records:
        record_dict = {}
        for c in r.__table__.columns:
            val = getattr(r, c.name)
            if isinstance(val, datetime):
                record_dict[c.name] = val.isoformat()
            elif isinstance(val, uuid.UUID):
                record_dict[c.name] = str(val)
            else:
                record_dict[c.name] = val
                
        # Attach HLC to the outgoing record
        r_updated_at = getattr(r, "updated_at")
        if r_updated_at.tzinfo is None:
            r_updated_at = r_updated_at.replace(tzinfo=timezone.utc)
        r_timestamp = int(r_updated_at.timestamp() * 1000)
        r_counter = getattr(r, "row_version", 0)
        r_hlc = HLC(timestamp=r_timestamp, counter=r_counter, node_id=server_node_id)
        record_dict["hlc"] = r_hlc.to_string()
        
        result_list.append(record_dict)
        
    return result_list
