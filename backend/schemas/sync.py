from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class SyncPayload(BaseModel):
    categories: List[Dict[str, Any]] = []
    products: List[Dict[str, Any]] = []
    orders: List[Dict[str, Any]] = []
    order_items: List[Dict[str, Any]] = []
    payments: List[Dict[str, Any]] = []
    outlet_stock: List[Dict[str, Any]] = []
    shifts: List[Dict[str, Any]] = []
    cash_activities: List[Dict[str, Any]] = []
    ingredients: List[Dict[str, Any]] = []
    recipes: List[Dict[str, Any]] = []
    recipe_ingredients: List[Dict[str, Any]] = []

class SyncRequest(BaseModel):
    last_sync_hlc: Optional[str] = None
    node_id: str
    # outlet_id: wajib untuk multi-outlet tenant (Pro+ yang punya >1 outlet).
    # Backward compat: single-outlet tenant boleh None → server auto-pick.
    # Multi-outlet tenant tanpa outlet_id → 400 (cegah cross-outlet leak).
    outlet_id: Optional[str] = None
    # idempotency_key: client-generated (UUID) per batch push. Kalau retry
    # karena network flaky, kirim key yang sama → server skip push (dedup),
    # pull tetap jalan. Cegah double stock deduct offline order.
    idempotency_key: Optional[str] = None
    # Cursor pagination (CRITICAL #7): cursor_hlc = pagination cursor (intra-
    # session, advance per page). Client yang baru start pake last_sync_hlc,
    # lanjutan pake cursor_hlc. Server skip PUSH kalau cursor_hlc di-set
    # (push sudah jalan di first page, lanjutan cuma pull).
    cursor_hlc: Optional[str] = None
    # ID tie-break untuk handle duplikat tuple (updated_at, row_version).
    # Kombinasi (hlc, id) = unique untuk setiap row karena id UUID. Kalau
    # client gak kirim, tolerate 1-row miss kasus edge duplicate tuple.
    cursor_last_id: Optional[str] = None
    # Max records per table per response. Default 500 — compromise antara
    # throughput (besar lebih dikit roundtrip) dan memory/latency (kecil
    # lebih aman untuk mobile + low bandwidth). Server cap di 2000.
    limit: int = Field(default=500, ge=10, le=2000)
    changes: SyncPayload

class SyncResponse(BaseModel):
    last_sync_hlc: str
    changes: SyncPayload
    stock_mode: Optional[str] = None
    subscription_tier: Optional[str] = None
    # Pagination metadata — client loop sampai has_more == False.
    has_more: bool = False
    # Cursor untuk request berikutnya. None kalau has_more False.
    next_cursor_hlc: Optional[str] = None
    # ID record terakhir di batch ini (kombo dgn next_cursor_hlc untuk unique
    # tie-break). Kirim balik sebagai cursor_last_id di request berikutnya.
    next_cursor_last_id: Optional[str] = None
