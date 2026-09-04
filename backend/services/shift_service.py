"""
Shift otomatis — satu mesin buat semua profil (ringan / standar / ketat).

Latar (2 Sep 2026): 25 dari 27 shift di produksi terbuka lebih dari sehari.
Toggle buka/tutup yang wajib kalah di lapangan, dan tiga jalur transaksi
(order, bayar, tab) masing-masing nyari shift dengan caranya sendiri sampai
kasir bisa mentok "Buka shift dulu" padahal Beranda nulis "Shift aktif".

Aturan mesin:
- Sesi itu PER OUTLET (laci bersama), siapa pun yang membukanya. Siapa input
  apa tetap dibaca dari `orders.user_id`.
- `ensure_open_shift()` = satu-satunya jalan transaksi dapat shift. Nggak ada
  → dibuka sendiri (`opened_by='auto'`), modal awal = sisa penutupan
  terakhir. Nggak pernah raise "buka shift dulu".
- Ditutup sendiri di batas hari usaha 04.00 waktu outlet oleh janitor
  (`backend/tasks/shift_cutoff.py`). Yang ditutup sistem TIDAK dihitung:
  `ending_cash` dan `counted_at` NULL. Angka selisih cuma lahir dari orang
  yang benar-benar menghitung.
- `paused` = "hitung nanti" (rujukan cash drawer Toast): laci lama dijeda,
  laci baru langsung jalan, penjualan nggak berhenti. Yang dijeda masih bisa
  dihitung (ditutup) kapan saja; kalau sampai 04.00 nggak dihitung, ikut
  ditutup janitor sebagai belum dihitung.

Semua fungsi di sini nggak commit. Pemanggil yang commit.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.shift import Shift, CashActivity, ShiftStatus, CashActivityType
from backend.models.payment import Payment
from backend.services.audit import log_audit

logger = logging.getLogger(__name__)

# Batas hari usaha: jam 4 pagi waktu outlet. Sama dengan default Toast, dan
# masuk akal buat warkop yang tutup lewat tengah malam.
BUSINESS_DAY_CUTOFF_HOUR = 4


def business_day_cutoff(now_utc: datetime, tz_name: str = "Asia/Jakarta") -> datetime:
    """Batas hari usaha TERAKHIR yang sudah lewat, dalam UTC.

    Sekarang 02.30 WIB → batasnya kemarin 04.00. Sekarang 09.00 WIB → hari ini
    04.00. Shift yang mulai SEBELUM batas ini sudah lewat hari usahanya.
    """
    try:
        tz = ZoneInfo(tz_name or "Asia/Jakarta")
    except Exception:
        tz = ZoneInfo("Asia/Jakarta")
    local_now = now_utc.astimezone(tz)
    cutoff_local = local_now.replace(hour=BUSINESS_DAY_CUTOFF_HOUR, minute=0, second=0, microsecond=0)
    if local_now < cutoff_local:
        cutoff_local -= timedelta(days=1)
    return cutoff_local.astimezone(timezone.utc)


async def get_open_shift(db: AsyncSession, outlet_id: UUID) -> Optional[Shift]:
    """Shift terbuka di outlet ini, yang paling baru. `.first()` karena data
    lama bisa nyimpen lebih dari satu."""
    q = (
        select(Shift)
        .where(
            Shift.outlet_id == outlet_id,
            Shift.status == ShiftStatus.open,
            Shift.deleted_at.is_(None),
        )
        .order_by(Shift.start_time.desc())
    )
    return (await db.execute(q)).scalars().first()


async def _last_closing_cash(db: AsyncSession, outlet_id: UUID) -> float:
    """Modal awal buat sesi otomatis = sisa laci dari penutupan terakhir.
    Kalau yang terakhir nggak dihitung, pakai perkiraannya."""
    q = (
        select(Shift)
        .where(
            Shift.outlet_id == outlet_id,
            Shift.status.in_([ShiftStatus.closed, ShiftStatus.paused]),
            Shift.deleted_at.is_(None),
        )
        .order_by(Shift.start_time.desc())
    )
    last = (await db.execute(q)).scalars().first()
    if not last:
        return 0.0
    if last.ending_cash is not None:
        return float(last.ending_cash)
    if last.expected_ending_cash is not None:
        return float(last.expected_ending_cash)
    return 0.0


async def ensure_open_shift(
    db: AsyncSession,
    outlet_id: UUID,
    user_id: UUID,
    tenant_id: Optional[UUID] = None,
    *,
    source: str = "transaction",
    strict: bool = True,
) -> Shift:
    """Ambil shift terbuka di outlet; kalau nggak ada, buka sendiri.

    Ini pengganti tiga pencarian shift lama di orders.py, payments.py, dan
    tab_service.py yang masing-masing bisa nolak transaksi. Kasir nggak pernah
    lagi dihadang "buka shift dulu".
    """
    shift = await get_open_shift(db, outlet_id)
    if shift:
        if strict:
            await assert_can_use_shift(db, shift, user_id)
        return shift

    # Profil Ketat: sesi TIDAK terbuka sendiri. Serah terima modal awal itu
    # intinya, jadi di sini transaksi memang dihadang — satu-satunya tempat
    # di seluruh mesin yang boleh bilang "buka kasir dulu".
    # strict=False (sync offline): penjualannya udah kejadian di HP, nggak
    # ada gunanya nolak; dibuka otomatis dan dicatat asalnya.
    if strict and await outlet_shift_mode(db, outlet_id) == "ketat":
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail={"code": "SHIFT_REQUIRED",
                    "message": "Sesi kas belum dibuka. Buka kasir dan isi modal awal untuk memulai."},
        )

    shift = Shift(
        outlet_id=outlet_id,
        user_id=user_id,
        status=ShiftStatus.open,
        starting_cash=await _last_closing_cash(db, outlet_id),
        opened_by="auto",
        notes=f"Dibuka otomatis ({source})",
    )
    db.add(shift)
    await db.flush()
    await log_audit(
        db=db, action="OPEN_SHIFT_AUTO", entity="shift", entity_id=shift.id,
        after_state={"starting_cash": float(shift.starting_cash), "source": source},
        user_id=user_id, tenant_id=tenant_id,
    )
    logger.info("shift auto-opened outlet=%s by=%s source=%s", outlet_id, user_id, source)
    return shift


async def compute_expected_cash(db: AsyncSession, shift: Shift) -> float:
    """modal awal + kas masuk (tunai) + pemasukan kas − pengeluaran kas."""
    act_q = (
        select(CashActivity.activity_type, func.sum(CashActivity.amount).label("total"))
        .where(CashActivity.shift_id == shift.id, CashActivity.deleted_at.is_(None))
        .group_by(CashActivity.activity_type)
    )
    totals = {row.activity_type: float(row.total or 0) for row in (await db.execute(act_q)).all()}
    income = totals.get(CashActivityType.income, 0.0)
    expense = totals.get(CashActivityType.expense, 0.0)

    cash_q = select(func.sum(Payment.amount_paid - func.coalesce(Payment.change_amount, 0))).where(
        Payment.shift_session_id == shift.id,
        Payment.payment_method == "cash",
        Payment.status == "paid",
        Payment.deleted_at.is_(None),
    )
    cash_in = float((await db.execute(cash_q)).scalar() or 0)
    return float(shift.starting_cash or 0) + income - expense + cash_in


async def close_shift(
    db: AsyncSession,
    shift: Shift,
    *,
    reason: str,
    user_id: Optional[UUID] = None,
    tenant_id: Optional[UUID] = None,
    ending_cash: Optional[float] = None,
    end_time: Optional[datetime] = None,
    notes: Optional[str] = None,
) -> dict:
    """Tutup shift (open atau paused).

    `ending_cash` None = ditutup tanpa dihitung: `counted_at` tetap NULL dan
    nggak ada angka selisih. Jangan pernah isi 0 di sini buat "biar rapi".
    """
    expected = await compute_expected_cash(db, shift)
    now = datetime.now(timezone.utc)

    shift.status = ShiftStatus.closed
    shift.end_time = end_time or now
    shift.expected_ending_cash = expected
    shift.closed_reason = reason
    shift.closed_by_user_id = user_id
    if ending_cash is not None:
        shift.ending_cash = ending_cash
        shift.counted_at = now
    if notes:
        shift.notes = notes if not shift.notes else f"{shift.notes} | {notes}"
    shift.row_version = (shift.row_version or 0) + 1

    variance = None
    variance_status = None
    if ending_cash is not None:
        variance = float(ending_cash) - expected
        variance_status = "balanced" if abs(variance) < 1 else ("surplus" if variance > 0 else "deficit")

    await log_audit(
        db=db, action="CLOSE_SHIFT", entity="shift", entity_id=shift.id,
        after_state={
            "reason": reason,
            "ending_cash": ending_cash,
            "expected_ending_cash": round(expected, 2),
            "variance": None if variance is None else round(variance, 2),
        },
        user_id=user_id, tenant_id=tenant_id,
    )
    return {"expected": expected, "variance": variance, "variance_status": variance_status}


async def count_closed_shift(
    db: AsyncSession,
    shift: Shift,
    *,
    ending_cash: float,
    user_id: Optional[UUID] = None,
    tenant_id: Optional[UUID] = None,
    notes: Optional[str] = None,
) -> dict:
    """Hitung kas sesi yang SUDAH ditutup tanpa dihitung (auto_cutoff 04.00,
    atau ditutup manual tanpa angka). Bug 4 Sep: tombol Hitung di app nembak
    /close, dan /close nolak semua yang statusnya closed, jadi sesi yang
    ditutup janitor nggak pernah bisa dihitung. Status, end_time, dan
    closed_reason TIDAK disentuh: yang ditambah cuma angka fisik + counted_at.
    """
    expected = shift.expected_ending_cash
    if expected is None:
        expected = await compute_expected_cash(db, shift)
        shift.expected_ending_cash = expected
    expected = float(expected)
    now = datetime.now(timezone.utc)
    shift.ending_cash = ending_cash
    shift.counted_at = now
    if notes:
        shift.notes = notes if not shift.notes else f"{shift.notes} | {notes}"
    shift.row_version = (shift.row_version or 0) + 1
    variance = float(ending_cash) - expected
    variance_status = "balanced" if abs(variance) < 1 else ("surplus" if variance > 0 else "deficit")
    await log_audit(
        db=db, action="COUNT_SHIFT", entity="shift", entity_id=shift.id,
        after_state={
            "ending_cash": ending_cash,
            "expected_ending_cash": round(expected, 2),
            "variance": round(variance, 2),
            "closed_reason": shift.closed_reason,
        },
        user_id=user_id, tenant_id=tenant_id,
    )
    return {"expected": expected, "variance": variance, "variance_status": variance_status}


async def pause_shift(
    db: AsyncSession,
    shift: Shift,
    user_id: UUID,
    tenant_id: Optional[UUID] = None,
) -> tuple[Shift, Optional[Shift]]:
    """"Hitung nanti": jeda shift ini, buka shift baru yang langsung aktif.

    Modal awal shift baru = perkiraan sisa laci yang dijeda. Di warung uangnya
    memang nggak pindah ke mana-mana pas ganti orang; yang berubah cuma siapa
    yang pegang. Selisih yang sebenarnya baru ketahuan waktu yang dijeda
    dihitung.
    """
    expected = await compute_expected_cash(db, shift)
    now = datetime.now(timezone.utc)

    shift.status = ShiftStatus.paused
    shift.paused_at = now
    shift.expected_ending_cash = expected
    shift.row_version = (shift.row_version or 0) + 1

    if await outlet_shift_mode(db, shift.outlet_id) == "ketat":
        # Serah terima eksplisit: kasir berikutnya buka sendiri dengan modal
        # awal. Nggak ada sesi lanjutan otomatis.
        await log_audit(
            db=db, action="PAUSE_SHIFT", entity="shift", entity_id=shift.id,
            after_state={"expected_ending_cash": round(expected, 2), "continued_by": None},
            user_id=user_id, tenant_id=tenant_id,
        )
        return shift, None

    new_shift = Shift(
        outlet_id=shift.outlet_id,
        user_id=user_id,
        status=ShiftStatus.open,
        starting_cash=expected,
        opened_by="auto",
        notes="Dibuka otomatis (lanjutan dari shift yang dijeda)",
    )
    db.add(new_shift)
    await db.flush()

    await log_audit(
        db=db, action="PAUSE_SHIFT", entity="shift", entity_id=shift.id,
        after_state={"expected_ending_cash": round(expected, 2), "continued_by": str(new_shift.id)},
        user_id=user_id, tenant_id=tenant_id,
    )
    return shift, new_shift


# ───────────────────────── gelombang 2: profil, peserta, blind close ─────────────────────────

SHIFT_MODES = ("ringan", "standar", "ketat")


async def is_owner(db: AsyncSession, user) -> bool:
    """Pemilik = akun yang daftar (is_superuser) atau peran bernama Owner.
    Kasir yang dibikin dari dashboard punya role_id NULL dan is_superuser False."""
    if getattr(user, "is_superuser", False):
        return True
    role_id = getattr(user, "role_id", None)
    if not role_id:
        return False
    from backend.models.role import Role
    role = await db.get(Role, role_id)
    return bool(role and (role.name or "").strip().lower() == "owner")


async def shift_participants(db: AsyncSession, shift: Shift) -> list[dict]:
    """Daftar hadir: siapa saja yang menginput pesanan di sesi ini, plus yang
    membuka dan yang menutup. DIHITUNG dari orders.user_id, bukan disimpan —
    sama prinsipnya dengan laba rugi dan segmen pelanggan: nggak ada tabel
    yang bisa basi."""
    from backend.models.order import Order
    from backend.models.user import User

    rows = (await db.execute(
        select(
            Order.user_id,
            func.count(Order.id).label("orders"),
            func.min(Order.created_at).label("first_seen"),
            func.max(Order.created_at).label("last_seen"),
        )
        .where(Order.shift_session_id == shift.id, Order.deleted_at.is_(None), Order.user_id.isnot(None))
        .group_by(Order.user_id)
    )).all()

    by_user: dict = {}
    for r in rows:
        by_user[r.user_id] = {"user_id": str(r.user_id), "orders": int(r.orders),
                              "first_seen": r.first_seen, "last_seen": r.last_seen}
    for uid, tag in ((shift.user_id, "opened"), (shift.closed_by_user_id, "closed")):
        if uid and uid not in by_user:
            by_user[uid] = {"user_id": str(uid), "orders": 0, "first_seen": None, "last_seen": None}
        if uid:
            by_user[uid][tag] = True

    if not by_user:
        return []
    users = (await db.execute(select(User.id, User.full_name).where(User.id.in_(list(by_user.keys()))))).all()
    names = {u.id: u.full_name for u in users}
    out = []
    for uid, d in by_user.items():
        d["name"] = names.get(uid) or "Kasir"
        d.setdefault("opened", False)
        d.setdefault("closed", False)
        out.append(d)
    out.sort(key=lambda d: (not d["opened"], -(d["orders"])))
    return out


def blind_close_for(mode: str, owner: bool) -> bool:
    """Blind close (rujukan Toast): kasir mengetik hitungan tanpa lihat angka
    harapan. Cuma berlaku kalau yang menghitung bukan pemilik, dan profilnya
    bukan Ringan. Pemilik selalu lihat semua."""
    return (mode or "ringan") != "ringan" and not owner


def blind_view(data: dict) -> dict:
    """Buang angka yang bikin hitungan bisa dicontek."""
    for k in ("expected_ending_cash", "total_cash_sales", "total_qris_sales", "starting_cash", "variance", "variance_status"):
        if k in data:
            data[k] = None
    for p in data.get("cash_payments") or []:
        p.pop("amount", None); p.pop("net_amount", None); p.pop("change_amount", None)
    for r in data.get("review") or []:
        for k in ("cash", "qris", "other", "total"):
            r[k] = None
    data["blind_close"] = True
    return data


async def outlet_shift_mode(db: AsyncSession, outlet_id: UUID) -> str:
    from backend.models.outlet import Outlet
    mode = (await db.execute(select(Outlet.shift_mode).where(Outlet.id == outlet_id))).scalar()
    return mode or "ringan"


async def uncounted_shifts(db: AsyncSession, outlet_id: UUID, days: int = 14) -> list[Shift]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    return list((await db.execute(
        select(Shift).where(
            Shift.outlet_id == outlet_id,
            Shift.deleted_at.is_(None),
            Shift.counted_at.is_(None),
            Shift.status.in_([ShiftStatus.paused, ShiftStatus.closed]),
            Shift.start_time >= since,
        ).order_by(Shift.start_time.desc())
    )).scalars().all())



# ───────────────────────── gelombang 3: Ketat ─────────────────────────

async def assert_can_use_shift(db: AsyncSession, shift: Shift, user_id: UUID) -> None:
    """Lockdown: laci yang dikunci cuma bisa dipakai kasir pemegangnya.
    Pemilik menerobos (rujukan Toast: manager override)."""
    locked = getattr(shift, "locked_user_id", None)
    if not locked or locked == user_id:
        return
    from backend.models.user import User
    user = await db.get(User, user_id)
    if user and await is_owner(db, user):
        return
    holder = await db.get(User, locked)
    from fastapi import HTTPException
    raise HTTPException(
        status_code=403,
        detail={"code": "SHIFT_LOCKED",
                "message": f"Laci sedang dipegang {holder.full_name if holder else 'kasir lain'}. "
                           "Minta dia menjeda atau menutup sesinya dulu (serah terima)."},
    )


async def shift_review(db: AsyncSession, shift: Shift) -> list[dict]:
    """Rekap per kasir: pesanan, tunai, QRIS, total. Dihitung dari orders dan
    payments di sesi ini; bahan layar tutup kasir dan dashboard pemilik."""
    from backend.models.order import Order
    from backend.models.user import User

    rows = (await db.execute(
        select(
            Order.user_id,
            func.count(func.distinct(Order.id)).label("orders"),
            func.coalesce(func.sum(
                case((Payment.payment_method == "cash",
                           Payment.amount_paid - func.coalesce(Payment.change_amount, 0)), else_=0)
            ), 0).label("cash"),
            func.coalesce(func.sum(
                case((Payment.payment_method == "qris", Payment.amount_paid), else_=0)
            ), 0).label("qris"),
            func.coalesce(func.sum(
                case((Payment.payment_method.notin_(["cash", "qris"]), Payment.amount_paid), else_=0)
            ), 0).label("other"),
        )
        .select_from(Order)
        .outerjoin(Payment, (Payment.order_id == Order.id) & (Payment.status == "paid") & (Payment.deleted_at.is_(None)))
        .where(Order.shift_session_id == shift.id, Order.deleted_at.is_(None), Order.user_id.isnot(None))
        .group_by(Order.user_id)
    )).all()
    if not rows:
        return []
    names = {u.id: u.full_name for u in (await db.execute(
        select(User.id, User.full_name).where(User.id.in_([r.user_id for r in rows])))).all()}
    out = []
    for r in rows:
        out.append({
            "user_id": str(r.user_id), "name": names.get(r.user_id) or "Kasir",
            "orders": int(r.orders), "cash": float(r.cash), "qris": float(r.qris), "other": float(r.other),
            "total": float(r.cash) + float(r.qris) + float(r.other),
        })
    out.sort(key=lambda d: -d["total"])
    return out
