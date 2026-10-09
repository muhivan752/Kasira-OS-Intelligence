"""Selaris AI: satu chat dengan alat (DeepSeek function calling). 9 Okt 2026.

Masalah yang ditutup (log chat Ivan 9/10): chat utama tidak tersambung ke
"atur bahan lewat percakapan", jadi menjawab "tidak bisa, lewat menu Settings"
lalu MENGARANG tabel HPP sendiri. Sekarang:

- Alat `susun_resep` memakai mesin HPP yang sudah ada (hpp_setup_service:
  draft_for + open_session). Modal dihitung kode dari harga bahan toko;
  penyimpanan tetap lewat approve HPP (kartu di chat / menu Atur bahan).
- Model dilarang menghitung HPP/modal/margin; angka disalin dari konteks atau
  hasil alat. Gaya: profesional, tanpa emoji, tanpa tanda pisah panjang.
- Konteks tambahan per izin: tim & absensi, jabatan & akses, saran terbuka.

Siapa boleh apa diputuskan oleh AccessContext yang sama dengan seluruh app.
"""
import json
import logging
import re
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select

logger = logging.getLogger(__name__)

STYLE = """
# GAYA DAN BATAS SELARIS AI (WAJIB)
- Nama kamu Selaris AI. Bahasa Indonesia profesional, ringkas, langsung ke inti, seperti konsultan usaha yang paham data toko.
- Tanpa emoji. Jangan pakai tanda pisah panjang; pakai koma, titik dua, atau kalimat baru. Jangan membuka dengan "Wah", "Oke siap", atau basa-basi.
- JANGAN PERNAH menghitung HPP, modal, margin, atau harga bahan sendiri, dan jangan memakai harga pasar karangan. Angka seperti itu hanya boleh disalin dari data konteks atau hasil alat.
- Kalau pengguna minta dibuatkan, diisi, dilengkapi, atau dihitung resep, bahan, takaran, atau HPP suatu produk: panggil alat susun_resep. Jangan menyuruh pengguna mencari menu lain dan jangan bilang tidak bisa.
- Kalau alat susun_resep tidak tersedia, jelaskan bahwa akun ini belum punya izin kelola HPP dan pemilik usaha bisa memberikannya di menu Tim & absensi.
- Kalau pengguna menyebut harga beli bahan berubah (naik, turun, sekarang sekian): panggil ubah_harga_bahan. Kalau menyebut barang datang, baru beli, atau stok masuk: panggil tambah_stok, satu panggilan untuk semua barang yang disebut. Salin jumlah, satuan, dan rupiah persis dari pengguna; 38 ribu = 38000, 1,5 juta = 1500000.
- Kalau pengguna minta harga jual menu diubah: panggil ubah_harga_jual. Salin harga akhir, naik/turun rupiah, atau naik/turun persen persis seperti ucapan pengguna; jangan menghitung harga barunya sendiri. Harga jual hanya bisa diubah pemilik usaha.
- Kalau alat bahan tidak tersedia, jelaskan bahwa akun ini belum punya izin untuk itu dan pemilik usaha bisa memberikannya di Jabatan dan izin.
- Alat hanya menyiapkan kartu. Jangan pernah bilang sudah tersimpan, stok sudah bertambah, atau harga sudah berubah. Katakan "cek kartunya lalu tekan Simpan".
"""

RECIPE_TOOL = {"type": "function", "function": {
    "name": "susun_resep",
    "description": ("Siapkan draf resep dan hitung HPP satu produk memakai bahan dan harga toko. Dipakai setiap kali "
                    "pengguna minta dibuatkan, diisi, dilengkapi, atau dihitung resep, bahan, takaran, atau HPP. "
                    "Draf belum tersimpan sampai pengguna menekan Simpan."),
    "parameters": {"type": "object", "properties": {
        "produk": {"type": "string", "description": "Nama produk persis seperti di daftar menu toko kalau ada."},
        "keterangan": {"type": "string", "description": "Takaran, porsi, atau harga yang DISEBUT pengguna, disalin apa adanya. Kosongkan kalau tidak ada."},
    }, "required": ["produk"]}}}

PERMISSION_LABELS = {
    "pos.sell": "jualan di kasir", "pos.refund": "refund", "pos.refund.approve": "setujui refund",
    "pos.discount.override": "diskon manual", "pos.shift.manage": "kelola shift", "pos.cash.manage": "kelola kas",
    "pos.kitchen": "layar dapur", "sales.view": "lihat penjualan", "sales.detail.view": "lihat rincian penjualan",
    "hpp.view": "lihat HPP", "hpp.manage": "kelola HPP dan resep", "hpp.approve": "setujui HPP",
    "stock.view": "lihat stok", "stock.receive": "terima stok", "stock.adjust": "koreksi stok",
    "purchasing.view": "lihat pembelian", "purchasing.manage": "kelola pembelian", "supplier.price.view": "lihat harga pemasok",
    "finance.view": "lihat keuangan", "finance.manage": "kelola keuangan", "customers.lookup": "cari pelanggan",
    "customers.view": "lihat pelanggan", "customers.manage": "kelola pelanggan", "customers.export": "ekspor pelanggan",
    "hris.self": "absensi sendiri", "hris.employees.manage": "kelola karyawan", "hris.schedules.manage": "kelola jadwal",
    "hris.attendance.manage": "kelola absensi", "hris.accounts.manage": "kelola akun karyawan",
    "access.manage": "atur jabatan dan akses", "ai.chat": "pakai Selaris AI",
}

_EMOJI = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF️]")


def clean(text: str) -> str:
    """Saringan terakhir untuk gaya (sama seperti stripAIDashes di Sefrekuensi)."""
    text = text.replace(" — ", ", ").replace(" – ", ", ").replace("—", ", ").replace("–", "-")
    return _EMOJI.sub("", text)


def can_draft_recipe(access, tenant) -> bool:
    from backend.services.subscription import is_pro_tier
    if not is_pro_tier(tenant):
        return False
    return access.mode == "owner" or all(access.allows(p) for p in ("ai.chat", "hpp.view", "supplier.price.view", "hpp.manage"))


# ───────────────────────── konteks tambahan ─────────────────────────

def _hm(dt, tz):
    return dt.astimezone(tz).strftime("%H.%M") if dt else None


async def team_context(db, access, outlet, user) -> str:
    """Tim & absensi, dihitung kode. Pemilik/pengelola: semua; karyawan: dirinya."""
    from backend.models.hris import HrAttendance, HrEmployee, HrSchedule
    manage = access.mode == "owner" or any(access.allows(p) for p in (
        "hris.attendance.manage", "hris.employees.manage", "hris.schedules.manage"))
    if not manage and not access.allows("hris.self"):
        return ""
    tz = ZoneInfo(outlet.timezone or "Asia/Jakarta")
    today = datetime.now(timezone.utc).astimezone(tz).date()
    month_start = today.replace(day=1)
    q = select(HrEmployee).where(HrEmployee.tenant_id == user.tenant_id, HrEmployee.outlet_id == outlet.id,
                                 HrEmployee.deleted_at.is_(None), HrEmployee.is_active.is_(True))
    if not manage:
        q = q.where(HrEmployee.user_id == user.id)
    emps = (await db.execute(q.order_by(HrEmployee.name))).scalars().all()
    if not emps:
        return "\n\nTIM DAN ABSENSI: belum ada data karyawan untuk outlet ini di menu Tim & absensi." if manage else ""
    ids = [e.id for e in emps]
    scheds = (await db.execute(select(HrSchedule).where(HrSchedule.tenant_id == user.tenant_id,
        HrSchedule.employee_id.in_(ids), HrSchedule.deleted_at.is_(None),
        HrSchedule.work_date >= month_start, HrSchedule.work_date <= today + timedelta(days=6)))).scalars().all()
    atts = (await db.execute(select(HrAttendance).where(HrAttendance.tenant_id == user.tenant_id,
        HrAttendance.employee_id.in_(ids), HrAttendance.deleted_at.is_(None),
        HrAttendance.work_date >= month_start, HrAttendance.work_date <= today))).scalars().all()
    sched = {(s.employee_id, s.work_date): s for s in scheds}
    att = {(a.employee_id, a.work_date): a for a in atts}
    lines = []
    for e in emps:
        s, a = sched.get((e.id, today)), att.get((e.id, today))
        if a and a.status == "hadir":
            late = int((a.clock_in - s.starts_at).total_seconds() // 60) if s and a.clock_in and a.clock_in > s.starts_at + timedelta(minutes=10) else 0
            now_ = f"masuk {_hm(a.clock_in, tz)}" + (f" (telat {late} menit)" if late else "") + (f", pulang {_hm(a.clock_out, tz)}" if a.clock_out else "")
        elif a:
            now_ = a.status + (f" ({a.reason.strip()[:80]})" if a.reason else "")
        elif s:
            now_ = "belum absen" if datetime.now(timezone.utc) < s.starts_at + timedelta(minutes=10) else "belum absen padahal jadwal sudah mulai"
        else:
            now_ = None
        jadwal = f"jadwal {_hm(s.starts_at, tz)} s.d. {_hm(s.ends_at, tz)}" if s else "tanpa jadwal"
        today_text = f"{jadwal}, {now_}" if now_ else jadwal
        count = {"hadir": 0, "telat": 0, "izin": 0, "sakit": 0, "cuti": 0, "libur": 0, "tanpa_catatan": 0}
        d = month_start
        while d <= today:
            a2, s2 = att.get((e.id, d)), sched.get((e.id, d))
            if a2:
                count[a2.status] = count.get(a2.status, 0) + 1
                if a2.status == "hadir" and s2 and a2.clock_in and a2.clock_in > s2.starts_at + timedelta(minutes=10):
                    count["telat"] += 1
            elif s2 and d < today:
                count["tanpa_catatan"] += 1
            d += timedelta(days=1)
        week = [f"{s3.work_date.strftime('%d/%m')} {_hm(s3.starts_at, tz)}" for (eid, wd), s3 in sorted(sched.items(), key=lambda x: x[0][1])
                if eid == e.id and today < wd <= today + timedelta(days=6)]
        lines.append(f"- {e.name} ({e.position}): hari ini {today_text}. Bulan ini: hadir {count['hadir']}, telat {count['telat']}, "
                     f"izin {count['izin']}, sakit {count['sakit']}, cuti {count['cuti']}, libur {count['libur']}, "
                     f"jadwal tanpa catatan absensi {count['tanpa_catatan']}." + (f" Jadwal 6 hari ke depan: {', '.join(week)}." if week else ""))
    scope = "semua karyawan outlet" if manage else "hanya data milik pengguna ini"
    return (f"\n\nTIM DAN ABSENSI ({scope}; dihitung Selaris per {today.strftime('%d/%m/%Y')}; telat = masuk lebih dari 10 menit "
            "sesudah jadwal; salin angka ini, jangan menghitung ulang):\n" + "\n".join(lines))


async def access_context(db, access, user) -> str:
    """Jabatan & hak akses, hanya untuk pemilik atau yang berizin atur akses."""
    if not (access.mode == "owner" or access.allows("access.manage")):
        return ""
    from backend.models.role import Role
    from backend.models.user import User
    from backend.services.access import role_permissions
    users = (await db.execute(select(User).where(User.tenant_id == user.tenant_id, User.deleted_at.is_(None),
        User.is_active.is_(True)).order_by(User.full_name))).scalars().all()
    roles = {r.id: r for r in (await db.execute(select(Role).where(Role.tenant_id == user.tenant_id,
        Role.deleted_at.is_(None)))).scalars().all()}
    lines = []
    for u in users[:60]:
        if u.is_superuser:
            lines.append(f"- {u.full_name}: pemilik usaha, semua akses.")
            continue
        role = roles.get(u.role_id)
        try:
            perms, mode, _ = role_permissions(u, role)
        except Exception:  # noqa: BLE001  jabatan rusak: laporkan apa adanya
            lines.append(f"- {u.full_name}: jabatan {role.name if role else 'tidak ada'}, pengaturan akses perlu diperbaiki.")
            continue
        labels = sorted(PERMISSION_LABELS.get(p, p) for p in perms)
        lines.append(f"- {u.full_name}: jabatan {role.name if role else 'tanpa jabatan'}; boleh: {', '.join(labels) or 'tidak ada'}.")
    return ("\n\nJABATAN DAN AKSES (akun aktif; izin yang tidak disebut berarti tidak dimiliki; "
            "pengaturan di menu Tim & absensi):\n" + "\n".join(lines))


async def suggestions_context(db, user, access, outlet_id) -> str:
    from backend.services import suggestions as svc
    try:
        data = await svc.list_for(db, user, access, outlet_id)
    except Exception:  # noqa: BLE001  saran itu tambahan, chat tetap jalan
        return ""
    if not data["open"]:
        return ""
    items = [{"jenis": s["kind"], "mendesak": s["urgent"], "dampak_per_bulan": s["impact_rp"],
              "fakta": {k: v for k, v in (s["facts"] or {}).items() if k not in ("preview",)}} for s in data["open"]]
    return ("\n\nSARAN SELARIS YANG SEDANG TERBUKA (angka dihitung Selaris; jelaskan memakai angka ini; "
            "keputusan diambil pengguna lewat kartu Saran di Beranda):\n" + json.dumps(items, ensure_ascii=False, default=str))


# ───────────────────────── alat ─────────────────────────

async def run_recipe_tool(db, *, user, access, outlet, produk: str, keterangan: str, user_message: str, guard=None):
    """Draf resep lewat mesin HPP. Balikin (hasil untuk model, kartu untuk layar)."""
    from sqlalchemy import text
    from backend.models.product import Product
    from backend.services import hpp_setup_service as hpp
    # Konteks RLS bersifat per transaksi; pasang lagi sebelum membaca.
    await db.execute(text("SELECT set_config('app.current_tenant_id', :t, true)"), {"t": str(user.tenant_id)})
    name = (produk or "").strip()[:150]
    products = (await db.execute(select(Product).where(Product.brand_id == outlet.brand_id,
        Product.deleted_at.is_(None)))).scalars().all()
    exact = [p for p in products if p.name.strip().casefold() == name.casefold()]
    near = exact or [p for p in products if name.casefold() in p.name.casefold()]
    product = near[0] if len(near) == 1 else None
    if product:
        name = product.name
    hint = "\n".join(x for x in (user_message, keterangan) if x and x.strip())
    draft, preview, msg = await hpp.draft_for(db, outlet.brand_id, name, hint)
    if not draft:
        return {"status": "gagal", "pesan": "Draf belum bisa disusun. Minta pengguna menyebut bahan utamanya."}, None
    if guard:
        await guard()  # kunci singkat hanya saat menyimpan sesi
    else:
        await db.execute(text("SELECT set_config('app.current_tenant_id', :t, true)"), {"t": str(user.tenant_id)})
    session = await hpp.open_session(db, user=user, access_version=access.version, outlet=outlet, draft=draft,
        preview=preview, message=msg, source="selaris_ai_chat",
        reply="Draf dari Selaris AI. Cek takarannya, koreksi kalau beda, lalu simpan.")
    await db.commit()
    base = float(product.base_price) if product and product.base_price else None
    total = float(preview["total_cost"]) if preview.get("total_cost") else None
    margin = round((base - total) / base * 100, 1) if base and total else None
    lines = [{"bahan": l["name"], "takaran": l["input_quantity"], "satuan": l["input_unit"] or l["unit"],
              "biaya": float(l["line_cost"]) if l["line_cost"] else None, "perkiraan": l["is_estimated"]} for l in preview["lines"]]
    result = {"status": "draf_siap" if preview["ready"] else "belum_lengkap", "produk": name,
              "produk_baru": preview["new_product"], "modal_per_porsi": total, "harga_jual": base,
              "margin_persen": margin, "bahan": lines, "yang_kurang": preview["missing"][:5],
              "catatan": "Belum tersimpan. Pengguna menekan Simpan di kartu, atau Ubah untuk mengoreksi."}
    card = {"type": "recipe_draft", "session_id": str(session.id), "revision": session.revision,
            "fingerprint": preview.get("fingerprint"), "ready": preview["ready"], "replaces_recipe": preview["replaces_recipe"],
            "product": name, "new_product": preview["new_product"], "total_cost": total, "base_price": base,
            "margin": margin, "lines": lines, "missing": preview["missing"][:5]}
    return result, card


# ───────────────────────── putaran agen ─────────────────────────

async def run(*, system: str, history: list, message: str, tools: list, execute):
    """Putaran chat dengan alat. Yield event SSE (dict). `execute(name, args)` → (hasil, kartu|None).

    Teks dialirkan langsung; kalau model memanggil alat, alat dijalankan lalu
    model menulis jawaban akhir dari hasilnya (maksimal 2 putaran alat).
    """
    from backend.services.llm_client import deepseek_tool_stream
    msgs = [{"role": "system", "content": system + STYLE}] + [
        {"role": m["role"], "content": m["content"]} for m in history if m.get("content")] + [
        {"role": "user", "content": message}]
    tokens, text_all = 0, []
    for round_ in range(3):
        calls, said = None, []
        async for kind, value in deepseek_tool_stream(messages=msgs, tools=tools if round_ < 2 else None):
            if kind == "text":
                piece = clean(value)
                said.append(piece)
                text_all.append(piece)
                yield {"type": "chunk", "content": piece}
            elif kind == "usage":
                tokens += value[0] + value[1]
            elif kind == "tool_calls":
                calls = value
        if not calls:
            break
        msgs.append({"role": "assistant", "content": "".join(said) or None, "tool_calls": [
            {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["arguments"] or "{}"}} for c in calls]})
        for c in calls:
            try:
                args = json.loads(c["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}
            label = {"susun_resep": f"Menyiapkan draf resep {args.get('produk', '')}",
                     "ubah_harga_bahan": f"Menyiapkan perubahan harga {args.get('bahan', '')}",
                     "tambah_stok": "Menyiapkan catatan bahan masuk",
                     "ubah_harga_jual": "Menyiapkan perubahan harga jual"}.get(c["name"], "Menyiapkan")
            yield {"type": "status", "content": label.strip() + "…"}
            try:
                result, card = await execute(c["name"], args)
            except Exception:  # noqa: BLE001
                logger.exception("selaris_agent: alat %s gagal", c["name"])
                result, card = {"status": "gagal", "pesan": "Alat sedang bermasalah. Sampaikan ke pengguna untuk mencoba lagi."}, None
            if card:
                yield card
            msgs.append({"role": "tool", "tool_call_id": c["id"], "content": json.dumps(result, ensure_ascii=False, default=str)})
    yield {"type": "_final", "text": "".join(text_all), "tokens": tokens}
