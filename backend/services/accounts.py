import asyncio
import hashlib
import hmac
import re
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select, text, update

from backend.core import security
from backend.core.config import settings
from backend.models import AccountChallenge, AuditLog, LoginSession, Tenant, User
from backend.services.redis import get_redis_client


def now():
    return datetime.now(timezone.utc)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def secret_code(user_id, request_id, purpose):
    return hmac.new(settings.SECRET_KEY.encode(), f"account-code:{user_id}:{request_id}:{purpose}".encode(), hashlib.sha256).hexdigest()


def fingerprint(body):
    # Keyed so an audit dump cannot be used to guess the submitted password.
    return hmac.new(settings.SECRET_KEY.encode(), body.model_dump_json().encode(), hashlib.sha256).hexdigest()


async def lock(db, key):
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": f"account:{key}"})


async def audit_replay(db, actor, body, action):
    await lock(db, f"request:{body.client_request_id}")
    previous = await db.scalar(select(AuditLog).where(AuditLog.entity == "account_access",
        AuditLog.after_state["client_request_id"].astext == str(body.client_request_id)))
    if previous:
        if previous.action != action or previous.user_id != actor or previous.after_state.get("fingerprint") != fingerprint(body):
            raise HTTPException(409, "Permintaan sudah dipakai dengan data berbeda")
        return previous.after_state["result"]


def add_audit(db, actor, tenant_id, body, action, entity_id, result):
    db.add(AuditLog(user_id=actor, tenant_id=tenant_id, action=action, entity="account_access", entity_id=entity_id,
        after_state={"client_request_id": str(body.client_request_id), "fingerprint": fingerprint(body), "result": result}))


async def limited(request, shop, username, purpose="password"):
    redis = await get_redis_client()
    # Both keys are atomic and fixed-window; no clear-on-success race.
    peer = request.client.host if request.client else "unknown"
    for kind, value, maximum in (("peer", peer, 60), ("identity", f"{shop}:{username}", 12)):
        key = f"account-rate:{purpose}:{kind}:{digest(value)}"
        attempts = await redis.eval("local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]) end; return n", 1, key, 900)
        if attempts > maximum:
            raise HTTPException(429, "Terlalu banyak percobaan. Coba lagi dalam 15 menit.")


async def issue_session(db, user, outlet_id=None):
    session_id = uuid4()
    expires = now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = security.create_access_token(user.id, session_id=session_id, credential_version=user.credential_version)
    db.add(LoginSession(id=session_id, tenant_id=user.tenant_id, user_id=user.id, outlet_id=outlet_id,
        token_hash=digest(token), expires_at=expires, credential_version=user.credential_version, row_version=1))
    db.add(AuditLog(tenant_id=user.tenant_id, user_id=user.id, action="session_login", entity="user",
        entity_id=user.id, after_state={"session_id": str(session_id)}))
    await db.flush()
    return token


async def validate_session(db, user, claims, token):
    sid = claims.get("sid")
    if not sid:
        if user.credential_version > 0:
            raise HTTPException(401, "Sesi lama berakhir. Masuk kembali dengan akun Anda.")
        return None
    try:
        sid = UUID(sid)
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(401, "Sesi tidak valid") from None
    row = await db.scalar(select(LoginSession).where(LoginSession.id == sid,
        LoginSession.user_id == user.id, LoginSession.tenant_id == user.tenant_id,
        LoginSession.deleted_at.is_(None)).execution_options(populate_existing=True))
    if (not row or row.revoked_at or not row.expires_at or row.expires_at <= now()
        or type(claims.get("cv")) is not int or claims["cv"] != user.credential_version
        or row.credential_version != user.credential_version
        or not hmac.compare_digest(row.token_hash, digest(token))):
        raise HTTPException(401, "Sesi telah berakhir. Silakan masuk kembali.")
    return row


async def revoke_all(db, user, clear_password=False):
    user.credential_version += 1
    user.row_version += 1
    if clear_password:
        user.password_hash = None
    await db.execute(update(LoginSession).where(LoginSession.tenant_id == user.tenant_id,
        LoginSession.user_id == user.id, LoginSession.revoked_at.is_(None))
        .values(revoked_at=now(), row_version=LoginSession.row_version + 1))
    await db.execute(update(AccountChallenge).where(AccountChallenge.tenant_id == user.tenant_id,
        AccountChallenge.user_id == user.id, AccountChallenge.consumed_at.is_(None))
        .values(consumed_at=now(), row_version=AccountChallenge.row_version + 1))


async def set_password(db, user, password):
    await revoke_all(db, user)
    user.password_hash = await asyncio.to_thread(security.get_password_hash, password)


async def challenge(db, user, request_id, purpose):
    code = secret_code(user.id, request_id, purpose)
    row = AccountChallenge(id=uuid4(), tenant_id=user.tenant_id, user_id=user.id,
        purpose=purpose, token_hash=digest(code), credential_version=user.credential_version,
        expires_at=now() + timedelta(hours=24 if purpose == "activation" else 24 * 365), row_version=1)
    db.add(row)
    await db.flush()
    return code


async def identity(db, shop, username):
    rows = (await db.scalars(select(User).join(Tenant, User.tenant_id == Tenant.id).where(
        Tenant.login_username == shop, Tenant.deleted_at.is_(None), User.login_username.in_(username_aliases(username)),
        User.deleted_at.is_(None)))).all()
    return rows[0] if len(rows) == 1 else None


def username_aliases(username):
    aliases = {username}
    if re.fullmatch(r"\d+", username):
        if username.startswith("0") and 8 <= len(username) + 1 <= 15:
            aliases.add("62" + username[1:])
        elif username.startswith("62") and 8 <= len(username) <= 15:
            aliases.add("0" + username[2:])
    return aliases


async def require_available_username(db, tenant_id, username, exclude_id=None):
    query = select(User.id).where(User.tenant_id == tenant_id, User.deleted_at.is_(None),
        User.login_username.in_(username_aliases(username)))
    if exclude_id:
        query = query.where(User.id != exclude_id)
    if await db.scalar(query):
        raise HTTPException(409, "Username atau nomor HP sudah dipakai oleh akun lain dalam bisnis ini")


async def password_matches(user, password):
    # The same work is done for an unknown user, avoiding a cheap account probe.
    hashed = user.password_hash if user and user.password_hash else DUMMY_PASSWORD_HASH
    valid = await asyncio.to_thread(security.verify_password, password, hashed)
    return bool(valid and user and user.password_hash)


DUMMY_PASSWORD_HASH = security.get_password_hash("dummy-password-never-a-login")
