from sqlalchemy import Column, String, DateTime, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from backend.core.database import Base


class Event(Base):
    """
    Append-only event store — Golden Rule #8: TIDAK BOLEH update/delete.
    Partitioned by hash(outlet_id) — lihat migration 037_events.py.

    stream_id convention:
      - product:{product_id}   → stock events (Starter + Pro)
      - order:{order_id}       → order lifecycle events
      - outlet:{outlet_id}     → outlet-level events

    event_type convention (stock):
      - stock.sale             → deduct dari transaksi (Starter)
      - stock.restock          → terima barang masuk (Starter)
      - stock.adjustment       → koreksi manual (Pro)
      - stock.waste            → pembuangan/expired (Pro)
    """
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), server_default=text('gen_random_uuid()'), primary_key=True)
    outlet_id = Column(UUID(as_uuid=True), nullable=False, primary_key=True)
    stream_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    event_data = Column(JSONB, nullable=True)
    event_metadata = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text('now()'), nullable=False)
