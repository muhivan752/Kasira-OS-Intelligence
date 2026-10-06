"""Fresh, scoped financial facts for the existing assistant; no financial writes."""
import json
import logging
import re
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from backend.models.outlet import Outlet
from backend.services import finance_service

logger = logging.getLogger(__name__)


def is_finance_question(message):
    return bool(re.search(r"\b(keuangan|pengeluaran|laba|untung|rugi|kas|cashflow|utang|hutang|biaya|tagihan|sewa|gaji|listrik|arus kas)\b", message, re.I))


def report_month(message, now=None):
    now = now or datetime.now(finance_service.WIB)
    explicit = re.search(r"\b([0-9]{4}-(?:0[1-9]|1[0-2]))\b", message)
    if explicit:
        finance_service.month_bounds(explicit.group(1))
        return explicit.group(1)
    year, month = now.year, now.month
    if re.search(r"\bbulan\s+(lalu|kemarin|sebelumnya)\b", message, re.I):
        month -= 1
        if month == 0:
            year -= 1; month = 12
    return f"{year:04d}-{month:02d}"


async def build_finance_context(message, outlet_id, tenant_id, db):
    if not is_finance_question(message):
        return ""
    try:
        async with db.begin_nested():
            outlet = (await db.execute(select(Outlet).where(
                Outlet.id == UUID(str(outlet_id)), Outlet.tenant_id == UUID(str(tenant_id)), Outlet.deleted_at.is_(None),
            ))).scalar_one_or_none()
            if not outlet:
                raise ValueError("Outlet financial context unavailable")
            data = await finance_service.summary(db, tenant_id=UUID(str(tenant_id)), outlet=outlet,
                                                 month=report_month(message), include_trend=False)
            facts = data.model_dump(mode="json", exclude={"trend"})
        return (
            "\n\nFAKTA KEUANGAN TERBARU (lebih utama daripada ringkasan cache atau angka percakapan lama):\n"
            + json.dumps(facts, ensure_ascii=False)
            + "\nSebutkan periode dan outlet saat menjawab angka. Data periode hanya untuk bulan pada month; "
            "jangan gunakan total bulanan untuk menjawab harian, mingguan, tahunan, atau bulan lain. "
            "Bila pengguna menyebut periode yang belum tersedia, minta bulan YYYY-MM atau arahkan ke Keuangan. "
            "Laba adalah perkiraan dengan HPP TERKINI dan biaya tercatat, penjualan termasuk pajak/service. "
            "Sebutkan HPP belum lengkap bila cogs_coverage < 1. cash_net adalah PERUBAHAN uang, bukan saldo. "
            "Utang dan overdue adalah posisi saat ini, bukan saldo akhir bulan historis. "
            "Pembayaran nota belum memiliki akun asal; cash_history_estimated berarti sebagian bulan bayar diperkirakan. "
            "Konteks ini hanya membaca data: jangan mengaku mencatat pengeluaran, membuat reminder, membayar, "
            "atau mentransfer uang. Untuk pencatatan arahkan ke Keuangan atau Nota belanja."
        )
    except Exception:
        logger.warning("Financial assistant context unavailable", exc_info=True)
        return "\n\nData keuangan terbaru belum tersedia. Jangan menjawab angka keuangan dari cache, riwayat, atau perkiraan sendiri. Minta pengguna memuat ulang Keuangan."
