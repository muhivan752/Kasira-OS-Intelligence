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
from decimal import Decimal
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

    if tenant_id is None:
        # Audit log ber-RLS menolak tenant_id NULL dan membatalkan seluruh
        # transaksi (kegigit tes 8 Okt: jalur storefront/refund manggil tanpa
        # tenant). Ambil dari outlet supaya pemanggil nggak bisa lupa.
        from backend.models.outlet import Outlet
        tenant_id = (await db.execute(select(Outlet.tenant_id).where(Outlet.id == outlet_id))).scalar()

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


# ───────────────────────── matematika laci ─────────────────────────
#
# Satu definisi, dipakai perkiraan laci, ringkasan sesi, DAN rekap per akun,
# supaya jumlah per akun selalu sama persis dengan angka laci (fix 8 Okt 2026).
#
#   Masuk(S)  = Σ (dibayar − kembalian) pembayaran TUNAI dengan
#               shift_session_id = S dan status paid ATAU refunded
#               (uangnya memang pernah masuk laci; refund dicatat terpisah).
#   Refund(S) = Σ refund TUNAI berstatus completed yang uangnya keluar di S:
#               metadata_payload.shift_session_id = S. Refund lama tanpa
#               penanda dihitung di sesi pembayarannya sendiri, jadi refund
#               penuh lama tetap netral (masuk − keluar = 0) seperti dulu.
#   Perkiraan = modal awal + pemasukan kas − pengeluaran kas + Masuk − Refund
#
# Rekap per akun = himpunan yang SAMA dikelompokkan: uang masuk per
# payments.processed_by, refund per payment_refunds.requested_by (orang di
# depan laci yang menyerahkan uang). NULL = "tanpa akun" (online, kurir,
# data lama). Σ semua baris == Masuk − Refund, tanpa pengecualian.

DRAWER_PAYMENT_STATUSES = ("paid", "refunded")
REVIEW_MONEY_KEYS = ("cash", "cash_refunds", "cash_net", "qris", "other", "total")
REFUND_SHIFT_KEY = "shift_session_id"


def _d(v) -> Decimal:
    return Decimal(str(v)) if v is not None else Decimal("0")


def payment_net(payment) -> Decimal:
    """Uang yang benar-benar tinggal di toko dari satu pembayaran."""
    return _d(payment.amount_paid) - _d(payment.change_amount)


def _refund_in_shift_clause(shift_id: UUID):
    from sqlalchemy import or_, and_
    from backend.models.payment_refund import PaymentRefund
    tagged = PaymentRefund.metadata_payload.op("->>")(REFUND_SHIFT_KEY)
    return or_(
        tagged == str(shift_id),
        and_(tagged.is_(None), Payment.shift_session_id == shift_id),
    )


async def _cash_in_by_user(db: AsyncSession, shift_id: UUID) -> dict:
    """{processed_by: {cash, qris, other}} dalam Decimal."""
    net = Payment.amount_paid - func.coalesce(Payment.change_amount, 0)
    rows = (await db.execute(
        select(
            Payment.processed_by,
            func.coalesce(func.sum(case((Payment.payment_method == "cash", net), else_=0)), 0).label("cash"),
            func.coalesce(func.sum(case((Payment.payment_method == "qris", net), else_=0)), 0).label("qris"),
            func.coalesce(func.sum(case((Payment.payment_method.notin_(["cash", "qris"]), net), else_=0)), 0).label("other"),
        )
        .where(
            Payment.shift_session_id == shift_id,
            Payment.status.in_(DRAWER_PAYMENT_STATUSES),
            Payment.deleted_at.is_(None),
        )
        .group_by(Payment.processed_by)
    )).all()
    return {r.processed_by: {"cash": _d(r.cash), "qris": _d(r.qris), "other": _d(r.other)} for r in rows}


async def _cash_refunds_by_user(db: AsyncSession, shift_id: UUID) -> dict:
    """{requested_by: Decimal} refund tunai yang uangnya keluar di sesi ini."""
    from backend.models.payment_refund import PaymentRefund
    who = func.coalesce(PaymentRefund.requested_by, PaymentRefund.approved_by)
    rows = (await db.execute(
        select(who.label("uid"), func.coalesce(func.sum(PaymentRefund.amount), 0).label("amt"))
        .select_from(PaymentRefund)
        .join(Payment, Payment.id == PaymentRefund.payment_id)
        .where(
            PaymentRefund.status == "completed",
            PaymentRefund.deleted_at.is_(None),
            Payment.payment_method == "cash",
            _refund_in_shift_clause(shift_id),
        )
        .group_by(who)
    )).all()
    return {r.uid: _d(r.amt) for r in rows}


async def drawer_totals(db: AsyncSession, shift: Shift) -> dict:
    """Semua komponen perkiraan laci, Decimal."""
    act_q = (
        select(CashActivity.activity_type, func.sum(CashActivity.amount).label("total"))
        .where(CashActivity.shift_id == shift.id, CashActivity.deleted_at.is_(None))
        .group_by(CashActivity.activity_type)
    )
    totals = {row.activity_type: _d(row.total) for row in (await db.execute(act_q)).all()}
    income = totals.get(CashActivityType.income, Decimal("0"))
    expense = totals.get(CashActivityType.expense, Decimal("0"))
    by_user = await _cash_in_by_user(db, shift.id)
    refunds = await _cash_refunds_by_user(db, shift.id)
    cash_in = sum((v["cash"] for v in by_user.values()), Decimal("0"))
    qris_in = sum((v["qris"] for v in by_user.values()), Decimal("0"))
    other_in = sum((v["other"] for v in by_user.values()), Decimal("0"))
    cash_refunds = sum(refunds.values(), Decimal("0"))
    starting = _d(shift.starting_cash)
    return {
        "starting_cash": starting,
        "cash_income": income,
        "cash_expense": expense,
        "cash_in": cash_in,
        "qris_in": qris_in,
        "other_in": other_in,
        "cash_refunds": cash_refunds,
        "expected": starting + income - expense + cash_in - cash_refunds,
    }


async def compute_expected_cash(db: AsyncSession, shift: Shift) -> float:
    """modal awal + pemasukan kas − pengeluaran kas + Masuk − Refund (lihat atas)."""
    return float((await drawer_totals(db, shift))["expected"])


async def attach_payment_to_drawer(
    db: AsyncSession,
    payment: Payment,
    *,
    actor_user_id: Optional[UUID] = None,
    fallback_user_id: Optional[UUID] = None,
    set_receiver: bool = True,
    source: str = "storefront",
) -> None:
    """Pasang pembayaran yang lahir di luar kasir (storefront, DP) ke sesi
    kas yang terbuka SAAT uangnya diterima, plus siapa penerimanya.

    Nggak pernah memindah pembayaran yang sudah punya sesi: sesi yang sudah
    dihitung nggak boleh berubah angkanya. `set_receiver=False` buat uang
    yang nggak lewat tangan orang (QRIS Xendit). Tanpa aktor dan tanpa
    cadangan, cuma nempel ke sesi yang sudah terbuka (link kurir).
    """
    if payment is None:
        return
    status = payment.status.value if hasattr(payment.status, "value") else str(payment.status)
    if status != "paid":
        return
    if payment.shift_session_id is None:
        opener = actor_user_id or fallback_user_id
        if opener:
            shift = await ensure_open_shift(db, payment.outlet_id, opener, strict=False, source=source)
        else:
            shift = await get_open_shift(db, payment.outlet_id)
        if shift is not None:
            payment.shift_session_id = shift.id
            payment.row_version = (payment.row_version or 0) + 1
    if set_receiver and actor_user_id and payment.processed_by is None:
        payment.processed_by = actor_user_id


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
    for k in ("expected_ending_cash", "total_cash_sales", "total_qris_sales", "starting_cash", "variance", "variance_status",
              "cash_refunds", "cash_income", "cash_expense"):
        if k in data:
            data[k] = None
    for p in data.get("cash_payments") or []:
        p.pop("amount", None); p.pop("net_amount", None); p.pop("change_amount", None)
    for r in data.get("review") or []:
        for k in REVIEW_MONEY_KEYS:
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
    """Rekap per akun untuk satu sesi.

    Dua ukuran yang sengaja dipisah (resto dengan waiter, 8 Okt 2026):
    - `orders`: pesanan yang DIINPUT akun ini (orders.user_id) = kinerja.
    - `cash`/`qris`/`other`/`cash_refunds`: uang yang DITERIMA akun ini
      (payments.processed_by), termasuk pembayaran tab.
    Baris `user_id: None` = uang tanpa akun (online, kurir, data lama).
    Σ (cash − cash_refunds) semua baris == Masuk − Refund di drawer_totals.
    """
    from backend.models.order import Order
    from backend.models.user import User

    money = await _cash_in_by_user(db, shift.id)
    refunds = await _cash_refunds_by_user(db, shift.id)
    order_rows = (await db.execute(
        select(Order.user_id, func.count(func.distinct(Order.id)).label("orders"))
        .where(Order.shift_session_id == shift.id, Order.deleted_at.is_(None), Order.user_id.isnot(None))
        .group_by(Order.user_id)
    )).all()
    orders = {r.user_id: int(r.orders) for r in order_rows}

    keys = set(money) | set(refunds) | set(orders)
    if not keys:
        return []
    ids = [k for k in keys if k is not None]
    names = {}
    if ids:
        names = {u.id: u.full_name for u in (await db.execute(
            select(User.id, User.full_name).where(User.id.in_(ids)))).all()}
    zero = Decimal("0")
    out = []
    for k in keys:
        m = money.get(k, {})
        cash, qris, other = m.get("cash", zero), m.get("qris", zero), m.get("other", zero)
        ref = refunds.get(k, zero)
        cash_net = cash - ref
        out.append({
            "user_id": str(k) if k else None,
            "name": (names.get(k) or "Akun terhapus") if k else "Tanpa akun (online/kurir)",
            "orders": orders.get(k, 0),
            "cash": float(cash),
            "cash_refunds": float(ref),
            "cash_net": float(cash_net),
            "qris": float(qris),
            "other": float(other),
            "total": float(cash_net + qris + other),
        })
    out.sort(key=lambda d: (d["user_id"] is None, -d["total"], -d["orders"]))
    return out
