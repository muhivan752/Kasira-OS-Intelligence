"""
Numpy-safe JSON encoder + SafeJSONResponse.

Pre-existing bug di /sync/ success path: `pydantic_core.PydanticSerialization
Error: Unable to serialize numpy.ndarray`. Product.embedding column (pgvector,
stored as list[float] in Postgres tapi loaded as numpy.ndarray via pg2py) leak
ke response serializer = 500.

Fix layered:
  1. Primary: sync.py skip `embedding` column di _row_to_dict + get_table_changes
     (Flutter client gak butuh embedding, cuma untuk AI similarity search
     backend-side)
  2. Defense-in-depth: custom encoder yg handle numpy types universally.
     Zero new dep (stdlib json + custom default fn).

SafeJSONResponse bisa di-set sbg `default_response_class` di FastAPI app —
route yang TIDAK pakai `response_model=...` (i.e. return dict langsung) akan
otomatis pake encoder ini. Route dgn response_model tetap lewat Pydantic
(tidak affect mereka).
"""

import json
import logging
from typing import Any

from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def safe_json_default(obj: Any) -> Any:
    """
    Fallback encoder untuk types yang stdlib json gak support.

    Supported conversions:
      - numpy.ndarray → list (via .tolist())
      - numpy scalars (int64, float64, etc) → Python primitive (via .item())
      - set / frozenset → list
      - Objects dengan .to_dict() method → dict
      - Objects dengan .isoformat() (datetime-like) → str
      - bytes → hex string (defensive — usually shouldn't reach here)

    Raise TypeError untuk types yg benar-benar tidak bisa encode — caller
    bakal dapat clear error message, bukan silent corruption.
    """
    # Numpy types — check via duck typing (avoid hard numpy import)
    if hasattr(obj, "tolist") and callable(obj.tolist):
        try:
            return obj.tolist()
        except Exception:
            pass
    if hasattr(obj, "item") and callable(obj.item):
        try:
            return obj.item()
        except Exception:
            pass

    # Collections
    if isinstance(obj, (set, frozenset)):
        return list(obj)

    # Date-like objects
    if hasattr(obj, "isoformat") and callable(obj.isoformat):
        try:
            return obj.isoformat()
        except Exception:
            pass

    # Bytes — hex for safety (actual content rarely needed in JSON)
    if isinstance(obj, (bytes, bytearray)):
        return obj.hex()

    # Pydantic models — rely on dict()
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump()
        except Exception:
            pass

    # No match — raise explicit error (better than silent corruption)
    raise TypeError(
        f"Object of type {type(obj).__name__} is not JSON serializable. "
        f"Add handler di backend/core/json_safe.py:safe_json_default() kalau type ini legit."
    )


class SafeJSONResponse(JSONResponse):
    """
    Drop-in replacement untuk JSONResponse — handles numpy + extra types.
    Set via FastAPI `default_response_class` untuk defense-in-depth.

    Note: route yg pakai `response_model=PydanticModel` TIDAK lewat sini
    (Pydantic punya serializer sendiri). Cuma protect route yang return
    dict/list langsung.
    """
    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            default=safe_json_default,
        ).encode("utf-8")
