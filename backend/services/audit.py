import json
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.audit_log import AuditLog
from backend.core.request_context import get_request_id

async def log_audit(
    db: AsyncSession,
    action: str,
    entity: str,
    entity_id: Any,
    before_state: Optional[Dict[str, Any]] = None,
    after_state: Optional[Dict[str, Any]] = None,
    user_id: Optional[Any] = None,
    tenant_id: Optional[Any] = None,
):
    """
    Write an audit log entry.
    """
    # Convert UUIDs to strings in state dicts if necessary, but JSONB usually handles it
    # if we use Pydantic models, we should dump them to dict first.
    
    audit_entry = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        before_state=before_state,
        after_state=after_state,
        request_id=get_request_id()
    )
    db.add(audit_entry)
    # We don't commit here, we let the caller commit the transaction
