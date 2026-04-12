from sqlalchemy import Column, String, DateTime, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from backend.core.database import Base


class Event(Base):
    """
    Append-only event store — Golden Rule #8: TIDAK BOLEH update/delete.
    Partitioned by hash(outlet_id) — lihat migration 037_events.py.

    stream_id convention:
      - product:{product_id}     → stock events (Starter + Pro)
      - ingredient:{id}          → ingredient lifecycle events
      - order:{order_id}         → order lifecycle events
      - payment:{payment_id}     → payment lifecycle events
      - outlet:{outlet_id}       → outlet-level events

    event_type convention:
      Stock:
        - stock.sale             → deduct dari transaksi
        - stock.restock          → terima barang masuk
        - stock.cancel_return    → return stock dari cancelled order
        - stock.adjustment       → koreksi manual (Pro)
        - stock.waste            → pembuangan/expired (Pro)
        - stock.ingredient_sale  → ingredient deduction via recipe
        - stock.ingredient_restock → ingredient restock (manual/ai_chat)
      Ingredient:
        - ingredient.created     → bahan baku baru
        - ingredient.price_updated → harga bahan berubah
      Order:
        - order.created          → order baru (source: pos/storefront)
        - order.preparing        → mulai diproses
        - order.ready            → siap diambil/diantar
        - order.completed        → selesai
        - order.cancelled        → dibatalkan
      Payment:
        - payment.pending        → menunggu pembayaran (QRIS)
        - payment.completed      → pembayaran berhasil
        - payment.failed         → pembayaran gagal

    All events carry source field: pos, storefront, xendit_webhook, ai_chat
    → Feeds into KG + AI context for Anthropic Claude analysis
    """
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), server_default=text('gen_random_uuid()'), primary_key=True)
    outlet_id = Column(UUID(as_uuid=True), nullable=False, primary_key=True)
    stream_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    event_data = Column(JSONB, nullable=True)
    event_metadata = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text('now()'), nullable=False)
