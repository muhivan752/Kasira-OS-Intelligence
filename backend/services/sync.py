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
                
        # Query existing record with FOR UPDATE to prevent race conditions during sync
        stmt = select(model_class).filter(model_class.id == record_id).with_for_update()
        result = await db.execute(stmt)
        db_record = result.scalar_one_or_none()
        
        if db_record:
            # Security/Tenant check: Ensure the existing record belongs to the correct tenant/outlet
            # If it doesn't match filter_kwargs, it means the client is trying to update a record they don't own
            is_authorized = True
            for k, v in filter_kwargs.items():
                if getattr(db_record, k) != v:
                    is_authorized = False
                    break
            
            if not is_authorized:
                continue # Skip unauthorized update
                
            # Financial Strict Strategy: Server wins if status is final
            if conflict_strategy == "financial_strict" and hasattr(db_record, "status"):
                if db_record.status in ["paid", "completed", "refunded", "cancelled"]:
                    continue # Skip update, server wins
            
            # Optimistic Locking & CRDT Conflict Resolution
            db_updated_at = db_record.updated_at
            if db_updated_at.tzinfo is None:
                db_updated_at = db_updated_at.replace(tzinfo=timezone.utc)
            
            db_timestamp = int(db_updated_at.timestamp() * 1000)
            db_counter = getattr(db_record, "row_version", 0)
            db_hlc = HLC(timestamp=db_timestamp, counter=db_counter, node_id=server_hlc.node_id)
            
            if client_hlc.compare(db_hlc) > 0:
                # Client wins
                for key, value in record.items():
                    # Map is_deleted from client to deleted_at
                    if key == "is_deleted":
                        if value and not db_record.deleted_at:
                            db_record.deleted_at = utc_now()
                        elif not value and db_record.deleted_at:
                            db_record.deleted_at = None
                        continue
                        
                    if hasattr(db_record, key) and key not in ["created_at", "updated_at", "row_version", "hlc"]:
                        # Handle datetime parsing if value is string
                        if isinstance(value, str) and (key.endswith('_at') or key == 'paid_at'):
                            try:
                                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                            except (ValueError, TypeError):
                                pass
                        setattr(db_record, key, value)
                
                # Update timestamp and increment row_version
                db_record.updated_at = utc_now()
                if hasattr(db_record, "row_version"):
                    db_record.row_version += 1
        else:
            # Insert new record
            # First check if the ID exists at all (to prevent IntegrityError if it belongs to another tenant)
            check_stmt = select(model_class).filter(model_class.id == record_id)
            check_result = await db.execute(check_stmt)
            if check_result.scalar_one_or_none():
                continue # ID exists but didn't match filter_kwargs earlier, skip to prevent crash
                
            for k, v in filter_kwargs.items():
                record[k] = v
                
            # Remove keys that don't exist in model
            valid_keys = {c.name for c in model_class.__table__.columns}
            clean_record = {}
            
            # Handle is_deleted mapping for new records
            if record.get("is_deleted"):
                clean_record["deleted_at"] = utc_now()
                
            for k, v in record.items():
                if k in valid_keys:
                    # Handle datetime parsing
                    if isinstance(v, str) and (k.endswith('_at') or k == 'paid_at'):
                        try:
                            v = datetime.fromisoformat(v.replace('Z', '+00:00'))
                        except (ValueError, TypeError):
                            pass
                    clean_record[k] = v
            
            new_record = model_class(**clean_record)
            if hasattr(new_record, "row_version"):
                new_record.row_version = 1
            db.add(new_record)
            
    await db.flush()

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
        
        # Use FOR UPDATE to prevent race conditions during PN-Counter merge
        stmt = select(OutletStock).filter(
            OutletStock.product_id == product_id,
            OutletStock.outlet_id == outlet_id
        ).with_for_update()
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
            
    await db.flush()

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
                
        # Map deleted_at to is_deleted for client
        record_dict["is_deleted"] = getattr(r, "deleted_at", None) is not None
                
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
