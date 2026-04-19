from pydantic import BaseModel
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
    changes: SyncPayload

class SyncResponse(BaseModel):
    last_sync_hlc: str
    changes: SyncPayload
    stock_mode: Optional[str] = None
    subscription_tier: Optional[str] = None
