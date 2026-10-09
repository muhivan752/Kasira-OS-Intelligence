"""Hapus akun (syarat Play Store + hak hapus UU PDP). Keputusan Ivan 9 Okt 2026.

Satu rumah untuk semua jalur hapus akun: endpoint web/app dan janitor.

- PEMILIK (`users.is_superuser`, akun yang mendaftarkan usaha) menghapus
  SELURUH usaha. Tidak langsung: `tenants.deletion_scheduled_at` = sekarang
  + 30 hari, bisa dibatalkan selama masa itu, toko tetap jalan normal.
  Sesudah lewat, `purge_due_once` menghapus semua datanya.
- SELAIN PEMILIK hanya menghapus akun login miliknya, LANGSUNG. Barisnya
  tidak dihapus (shifts.user_id RESTRICT, transaksi toko tetap milik toko),
  identitasnya dikosongkan dan semua sesi dicabut.

Yang SENGAJA disimpan sesudah purge (catatan keuangan PT dan milik toko
lain): baris `tenants` tanpa identitas, langganan dan tagihan langganan,
referral beserta komisinya. `referrals`/`referral_commissions` CASCADE dari
tenants, jadi menghapus baris tenant ikut menghapus komisi TOKO LAIN.

Urutan hapus DIHITUNG dari katalog Postgres tiap kali jalan, bukan daftar
tangan: tabel baru yang punya `tenant_id` atau FK ke tabel milik tenant
otomatis ikut. Ada tujuh FK RESTRICT/NO ACTION yang bikin `DELETE tenants`
polos gagal, makanya anak dihapus sebelum induk.

Pengaman berlapis: transaksi purge jalan dengan app.current_tenant_id =
tenant itu (role runtime kasira_app tidak bypass RLS), jadi predikat yang
salah pun tidak bisa menyentuh toko lain di tabel ber-RLS. Sesudah hapus,
setiap tabel dihitung ulang dan harus nol; kalau tidak, seluruh transaksi
dibatalkan dan log berteriak.
"""
import asyncio
import logging
import os
import re
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select, text

from backend.core.database import AsyncSessionLocal
from backend.models.tenant import Tenant

logger = logging.getLogger(__name__)

GRACE_DAYS = 30
CONFIRM_WORD = "HAPUS"
UPLOAD_DIR = "/app/uploads"
CHECK_INTERVAL_SECONDS = 3600
LOCK_KEY = "account_deletion:lock"

# Catatan keuangan PT + milik toko lain. Lihat docstring modul.
KEEP_TABLES = frozenset({
    "tenants", "subscriptions", "invoices", "subscription_invoices", "subscription_payments",
    "referrals", "referral_commissions",
    # Bukan milik tenant: agregat lintas toko tanpa identitas, log landing publik.
    "alembic_version", "platform_hpp_benchmarks", "platform_ingredient_prices",
    "platform_insights", "landing_chat_logs",
})
# Kolom penunjuk tanpa FK di skema (contoh: events.outlet_id, tabel partisi).
IMPLICIT_PARENTS = {"outlet_id": "outlets", "user_id": "users", "brand_id": "brands", "customer_id": "customers"}
_UPLOAD_RE = re.compile(r"/uploads/([A-Za-z0-9._-]+)")


def now():
    return datetime.now(timezone.utc)


def is_account_owner(user) -> bool:
    return user.is_superuser is True


async def status_for(db, user) -> dict:
    tenant = await db.get(Tenant, user.tenant_id)
    owner = is_account_owner(user)
    scheduled = tenant.deletion_scheduled_at if tenant else None
    return {
        "scope": "business" if owner else "account",
        "grace_days": GRACE_DAYS,
        "confirm_word": CONFIRM_WORD,
        "scheduled_at": scheduled.isoformat() if scheduled else None,
        "can_cancel": owner and scheduled is not None,
        "business_name": tenant.name if tenant else None,
    }


async def request_deletion(db, user, confirm: str) -> dict:
    if (confirm or "").strip().upper() != CONFIRM_WORD:
        raise HTTPException(400, f"Ketik {CONFIRM_WORD} untuk mengonfirmasi")
    tenant = await db.get(Tenant, user.tenant_id)
    if tenant is None:
        raise HTTPException(404, "Usaha tidak ditemukan")
    if not is_account_owner(user):
        await anonymize_user(db, user)
        await db.commit()
        logger.info("account_deletion: akun %s di tenant %s dihapus", user.id, user.tenant_id)
        return {"scope": "account", "deleted": True, "scheduled_at": None}
    if tenant.is_demo:
        raise HTTPException(400, "Akun demo tidak dapat dihapus")
    if tenant.deletion_scheduled_at is None:
        tenant.deletion_scheduled_at = now() + timedelta(days=GRACE_DAYS)
        tenant.deletion_requested_by = user.id
        await db.commit()
        logger.warning("account_deletion: tenant %s dijadwalkan dihapus %s oleh %s",
                       tenant.id, tenant.deletion_scheduled_at.isoformat(), user.id)
    return {"scope": "business", "deleted": False, "scheduled_at": tenant.deletion_scheduled_at.isoformat()}


async def cancel_deletion(db, user) -> dict:
    if not is_account_owner(user):
        raise HTTPException(403, "Hanya pemilik usaha yang dapat membatalkan")
    tenant = await db.get(Tenant, user.tenant_id)
    if tenant and tenant.deletion_scheduled_at is not None:
        tenant.deletion_scheduled_at = None
        tenant.deletion_requested_by = None
        await db.commit()
        logger.warning("account_deletion: jadwal hapus tenant %s dibatalkan oleh %s", tenant.id, user.id)
    return {"scope": "business", "scheduled_at": None}


async def anonymize_user(db, user):
    """Akun selain pemilik: identitas dikosongkan, login mati, baris tetap ada."""
    from backend.services.accounts import revoke_all
    await revoke_all(db, user, clear_password=True)
    user.full_name = "Akun dihapus"
    user.phone = None
    user.login_username = None
    user.pin_hash = None
    user.google_project_id = None
    user.google_uid = None
    user.google_email = None
    user.is_active = False
    user.deleted_at = now()
    await db.execute(text("DELETE FROM devices WHERE user_id = :u"), {"u": user.id})


# ───────────────────────── purge seluruh usaha ─────────────────────────

async def _catalog(db):
    tables = {r[0] for r in await db.execute(text(
        "SELECT relname FROM pg_class WHERE relnamespace = 'public'::regnamespace "
        "AND relkind IN ('r','p') AND NOT relispartition"))}
    cols = {}
    for t, c, dt in await db.execute(text(
            "SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_schema = 'public'")):
        cols.setdefault(t, {})[c] = dt
    fks = [tuple(r) for r in await db.execute(text(
        "SELECT c.conrelid::regclass::text, a.attname, c.confrelid::regclass::text, fa.attname "
        "FROM pg_constraint c "
        "JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1] "
        "JOIN pg_attribute fa ON fa.attrelid = c.confrelid AND fa.attnum = c.confkey[1] "
        "WHERE c.contype = 'f' AND array_length(c.conkey, 1) = 1 "
        "AND c.connamespace = 'public'::regnamespace"))]
    return tables, {t: cols.get(t, {}) for t in tables}, fks


def plan_purge(tables, cols, fks):
    """Hitung tabel milik tenant, predikat SQL tiap tabel, dan urutan hapus (anak dulu).

    Murni (tanpa DB) supaya bisa dites. Predikat memakai :tid.
    """
    edges = {}  # child -> [(col, parent, parent_col)]
    for child, col, parent, pcol in fks:
        if child != parent and child in tables and parent in tables:
            edges.setdefault(child, []).append((col, parent, pcol))
    for t in tables:
        declared = {c for c, _, _ in edges.get(t, [])}
        for col, parent in IMPLICIT_PARENTS.items():
            if col in cols[t] and col not in declared and parent != t and "id" in cols.get(parent, {}):
                edges.setdefault(t, []).append((col, parent, "id"))

    owned = {t for t in tables if "tenant_id" in cols[t] and t not in KEEP_TABLES}
    grew = True
    while grew:
        grew = False
        for t in sorted(tables - owned - KEEP_TABLES):
            if any(p in owned for _, p, _ in edges.get(t, [])):
                owned.add(t)
                grew = True

    preds = {}

    def pred(t, stack=()):
        if t in preds:
            return preds[t]
        if "tenant_id" in cols[t]:
            preds[t] = "tenant_id::text = :tid"
            return preds[t]
        parts = []
        for col, parent, pcol in edges.get(t, []):
            if parent in owned and parent not in stack:
                parts.append(f'"{col}" IN (SELECT "{pcol}" FROM "{parent}" WHERE {pred(parent, stack + (t,))})')
        if not parts:
            raise RuntimeError(f"tabel {t} tidak punya jalur ke tenant")
        preds[t] = "(" + " OR ".join(parts) + ")"
        return preds[t]

    for t in owned:
        pred(t)

    # Anak sebelum induk: tabel dihapus kalau tidak ada lagi tabel milik
    # tenant (yang belum dihapus) yang menunjuk ke dia.
    children = {t: set() for t in owned}
    for child in owned:
        for _, parent, _ in edges.get(child, []):
            if parent in owned and parent != child:
                children[parent].add(child)
    order, done = [], set()
    while len(done) < len(owned):
        ready = sorted(t for t in owned - done if children[t] <= done)
        if not ready:
            raise RuntimeError(f"siklus FK di antara: {sorted(owned - done)}")
        order.extend(ready)
        done.update(ready)
    return order, preds


async def purge_tenant(db, tenant_id) -> dict:
    """Hapus semua data satu usaha. Satu transaksi, dibatalkan kalau verifikasi gagal."""
    tid = str(tenant_id)
    await db.execute(text("SELECT set_config('app.current_tenant_id', :t, true)"), {"t": tid})
    tables, cols, fks = await _catalog(db)
    order, preds = plan_purge(tables, cols, fks)

    files, redis_keys = set(), set()
    for oid, slug in await db.execute(text("SELECT id, slug FROM outlets WHERE tenant_id::text = :tid"), {"tid": tid}):
        redis_keys.add(f"ai:context:{oid}")
        if slug:
            redis_keys.add(f"connect:storefront:{slug}")
    textual = {"text", "character varying", "json", "jsonb"}
    for t in order:
        for c, dt in cols[t].items():
            if dt in textual:
                rows = await db.execute(text(
                    f'SELECT "{c}"::text FROM "{t}" WHERE {preds[t]} AND "{c}"::text LIKE \'%/uploads/%\''), {"tid": tid})
                for (v,) in rows:
                    files.update(_UPLOAD_RE.findall(v or ""))

    counts = {}
    for t in order:
        res = await db.execute(text(f'DELETE FROM "{t}" WHERE {preds[t]}'), {"tid": tid})
        if res.rowcount:
            counts[t] = res.rowcount
    left = {}
    for t in order:
        n = await db.scalar(text(f'SELECT count(*) FROM "{t}" WHERE {preds[t]}'), {"tid": tid})
        if n:
            left[t] = n
    if left:
        raise RuntimeError(f"purge tenant {tid} menyisakan baris: {left}")

    await db.execute(text(
        "UPDATE subscription_invoices SET xendit_raw = NULL, notes = NULL WHERE tenant_id::text = :tid"), {"tid": tid})
    await db.execute(text(
        "UPDATE tenants SET name = 'Akun dihapus', login_username = NULL, owner_email = NULL, "
        "referral_code = NULL, is_active = false, deleted_at = now(), updated_at = now() WHERE id::text = :tid"),
        {"tid": tid})
    await db.commit()

    for name in files:
        try:
            os.remove(os.path.join(UPLOAD_DIR, name))
        except FileNotFoundError:
            pass
        except OSError:
            logger.warning("account_deletion: gagal hapus file %s", name, exc_info=True)
    if redis_keys:
        try:
            from backend.services.redis import get_redis_client
            await (await get_redis_client()).delete(*redis_keys)
        except Exception:  # noqa: BLE001  cache kedaluwarsa sendiri, purge sudah commit
            logger.warning("account_deletion: gagal hapus cache redis tenant %s", tid, exc_info=True)
    return {"tables": counts, "files": len(files)}


async def purge_due_once() -> int:
    # uvicorn 2 worker = 2 supervisor (lihat online_order_timeout). Kunci
    # Redis supaya satu worker saja; kalau Redis mati, FOR UPDATE SKIP LOCKED.
    try:
        from backend.services.redis import get_redis_client
        if not await (await get_redis_client()).set(LOCK_KEY, "1", nx=True, ex=CHECK_INTERVAL_SECONDS - 60):
            return 0
    except Exception:  # noqa: BLE001
        logger.warning("account_deletion: redis lock gagal, lanjut dengan SKIP LOCKED", exc_info=True)
    done = 0
    async with AsyncSessionLocal() as db:
        await db.execute(text("SET LOCAL app.current_tenant_id = ''"))
        due = [r[0] for r in await db.execute(select(Tenant.id).where(
            Tenant.deletion_scheduled_at.is_not(None), Tenant.deletion_scheduled_at <= now(),
            Tenant.deleted_at.is_(None), Tenant.is_demo.is_(False)))]
    for tid in due:
        async with AsyncSessionLocal() as db:
            try:
                locked = await db.scalar(text(
                    "SELECT id FROM tenants WHERE id = :tid AND deleted_at IS NULL AND is_demo = false "
                    "AND deletion_scheduled_at <= now() FOR UPDATE SKIP LOCKED"), {"tid": tid})
                if locked is None:
                    await db.rollback()
                    continue
                result = await purge_tenant(db, tid)
                done += 1
                logger.warning("account_deletion: tenant %s DIHAPUS, %s", tid, result)
            except Exception:  # noqa: BLE001  satu toko gagal tidak menahan yang lain
                await db.rollback()
                logger.exception("account_deletion: purge tenant %s GAGAL, dicoba lagi jam berikutnya", tid)
    return done


async def account_deletion_loop():
    while True:
        try:
            await purge_due_once()
        except Exception:  # noqa: BLE001
            logger.exception("account_deletion: loop error")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
