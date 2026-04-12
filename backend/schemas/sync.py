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
    changes: SyncPayload

class SyncResponse(BaseModel):
    last_sync_hlc: str
    changes: SyncPayload
