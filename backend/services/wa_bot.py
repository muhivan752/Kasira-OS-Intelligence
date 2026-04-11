"""
Kasira WhatsApp Bot — AI-powered customer service via Fonnte webhook

Flow: Customer WA → Fonnte Webhook → Intent Classify → Action → Reply via Fonnte

Intents:
- reservation_create: booking meja
- reservation_check: cek status reservasi
- reservation_cancel: cancel reservasi
- menu_inquiry: tanya menu/harga
- order_status: cek status pesanan
- greeting: salam/halo
- general: jam buka, alamat, dll
- unknown: bukan context outlet

Token optimization:
- Keyword-based intent detection first (no AI call for simple intents)
- Claude Haiku only for complex/ambiguous messages
- Context window: last 3 messages only
- Redis conversation state TTL 30 minutes
"""

import json
import logging
import re
from datetime import datetime, timezone, date, time, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.services.fonnte import send_whatsapp_message

logger = logging.getLogger(__name__)

# ─── Intent Keywords ────────────────────────────────────────────────────────

RESERVATION_CREATE_KW = [
    "reservasi", "booking", "book", "pesan meja", "mau reservasi",
    "mau booking", "mau pesan", "reserve", "daftar meja",
]
RESERVATION_CHECK_KW = [
    "cek reservasi", "status reservasi", "reservasi saya", "booking saya",
]
RESERVATION_CANCEL_KW = [
    "cancel", "batal", "batalkan reservasi", "cancel booking",
]
MENU_KW = [
    "menu", "daftar menu", "makanan", "minuman", "harga", "berapa harga",
    "ada apa aja", "apa aja", "list menu", "makan",
]
ORDER_STATUS_KW = [
    "pesanan", "order saya", "status pesanan", "udah jadi", "sampai mana",
]
GREETING_KW = [
    "halo", "hai", "hi", "hello", "selamat", "assalamualaikum", "pagi", "siang", "sore", "malam",
]
GENERAL_KW = [
    "jam buka", "buka jam", "tutup jam", "alamat", "lokasi", "dimana", "di mana",
    "parkir", "wifi", "smoking", "outdoor", "indoor",
]

# Conversation states
STATE_IDLE = "idle"
STATE_AWAITING_DATE = "awaiting_date"
STATE_AWAITING_TIME = "awaiting_time"
STATE_AWAITING_GUESTS = "awaiting_guests"
STATE_AWAITING_NAME = "awaiting_name"
STATE_CONFIRM_BOOKING = "confirm_booking"


def classify_wa_intent(message: str) -> str:
    msg = message.lower().strip()
    for kw in RESERVATION_CANCEL_KW:
        if kw in msg:
            return "reservation_cancel"
    for kw in RESERVATION_CHECK_KW:
        if kw in msg:
            return "reservation_check"
    for kw in RESERVATION_CREATE_KW:
        if kw in msg:
            return "reservation_create"
    for kw in MENU_KW:
        if kw in msg:
            return "menu_inquiry"
    for kw in ORDER_STATUS_KW:
        if kw in msg:
            return "order_status"
    for kw in GREETING_KW:
        if kw in msg:
            return "greeting"
    for kw in GENERAL_KW:
        if kw in msg:
            return "general"
    return "unknown"


# ─── Conversation State (Redis) ─────────────────────────────────────────────

async def get_conversation(redis_client, phone: str, outlet_id: str) -> dict:
    key = f"wa_conv:{outlet_id}:{phone}"
    try:
        data = await redis_client.get(key)
        if data:
            return json.loads(data)
    except Exception:
        pass
    return {"state": STATE_IDLE, "data": {}, "history": []}


async def save_conversation(redis_client, phone: str, outlet_id: str, conv: dict):
    key = f"wa_conv:{outlet_id}:{phone}"
    try:
        await redis_client.setex(key, 1800, json.dumps(conv, default=str))  # 30 min TTL
    except Exception:
        pass


async def clear_conversation(redis_client, phone: str, outlet_id: str):
    key = f"wa_conv:{outlet_id}:{phone}"
    try:
        await redis_client.delete(key)
    except Exception:
        pass


# ─── Action Handlers ─────────────────────────────────────────────────────────

async def handle_greeting(outlet_name: str, **kwargs) -> str:
    return (
        f"Halo! Selamat datang di *{outlet_name}* 👋\n\n"
        f"Ada yang bisa saya bantu?\n"
        f"• Ketik *menu* untuk lihat daftar menu\n"
        f"• Ketik *reservasi* untuk booking meja\n"
        f"• Ketik *jam buka* untuk info operasional"
    )


async def handle_menu(outlet_id: str, db: AsyncSession, **kwargs) -> str:
    from backend.models.product import Product
    from backend.models.outlet import Outlet
    from backend.models.category import Category

    outlet = (await db.execute(
        select(Outlet).where(Outlet.id == outlet_id)
    )).scalar_one_or_none()
    if not outlet or not outlet.brand_id:
        return "Maaf, data menu belum tersedia."

    products = (await db.execute(
        select(Product).where(
            Product.brand_id == outlet.brand_id,
            Product.is_active == True,
            Product.deleted_at.is_(None),
        ).order_by(Product.name)
    )).scalars().all()

    if not products:
        return "Maaf, belum ada menu yang tersedia saat ini."

    lines = [f"📋 *Menu {outlet.name}*\n"]
    for p in products:
        price = f"Rp{int(p.base_price):,}".replace(",", ".")
        stock_info = f" (habis)" if p.stock_enabled and p.stock_qty <= 0 else ""
        lines.append(f"• {p.name} — {price}{stock_info}")

    lines.append(f"\nMau pesan langsung atau reservasi meja? 😊")
    return "\n".join(lines)


async def handle_general(message: str, outlet_id: str, db: AsyncSession, **kwargs) -> str:
    from backend.models.outlet import Outlet
    outlet = (await db.execute(
        select(Outlet).where(Outlet.id == outlet_id)
    )).scalar_one_or_none()
    if not outlet:
        return "Maaf, informasi outlet belum tersedia."

    msg = message.lower()
    if any(kw in msg for kw in ["jam buka", "buka jam", "tutup jam", "jam operasional"]):
        hours = outlet.opening_hours or "Belum diatur"
        status = "BUKA" if outlet.is_open else "TUTUP"
        return f"🕐 *Jam Operasional {outlet.name}*\n{hours}\nStatus saat ini: *{status}*"

    if any(kw in msg for kw in ["alamat", "lokasi", "dimana", "di mana"]):
        addr = outlet.address or "Belum diatur"
        return f"📍 *Lokasi {outlet.name}*\n{addr}"

    return (
        f"ℹ️ *Info {outlet.name}*\n"
        f"📍 {outlet.address or '-'}\n"
        f"🕐 {outlet.opening_hours or '-'}\n"
        f"Status: {'BUKA' if outlet.is_open else 'TUTUP'}"
    )


async def handle_reservation_start(
    phone: str, outlet_id: str, outlet_name: str,
    redis_client, db: AsyncSession, **kwargs
) -> str:
    """Start reservation flow — ask for date."""
    conv = await get_conversation(redis_client, phone, outlet_id)
    conv["state"] = STATE_AWAITING_DATE
    conv["data"] = {}
    await save_conversation(redis_client, phone, outlet_id, conv)

    return (
        f"📅 *Reservasi Meja di {outlet_name}*\n\n"
        f"Mau reservasi untuk tanggal berapa?\n"
        f"Contoh: *besok*, *lusa*, *15 April*, *2026-04-15*"
    )


async def handle_reservation_check(
    phone: str, outlet_id: str, db: AsyncSession, **kwargs
) -> str:
    from backend.models.reservation import Reservation
    today = date.today()
    reservations = (await db.execute(
        select(Reservation).where(
            Reservation.outlet_id == outlet_id,
            Reservation.customer_phone == phone,
            Reservation.reservation_date >= today,
            Reservation.deleted_at.is_(None),
            Reservation.status.in_(["pending", "confirmed"]),
        ).order_by(Reservation.reservation_date.asc())
    )).scalars().all()

    if not reservations:
        return "Anda belum punya reservasi aktif. Ketik *reservasi* untuk booking meja."

    lines = ["📋 *Reservasi Aktif Anda:*\n"]
    for r in reservations:
        date_str = r.reservation_date.strftime("%d %B %Y") if r.reservation_date else "-"
        time_str = r.start_time.strftime("%H:%M") if r.start_time else "-"
        status = "✅ Dikonfirmasi" if r.status == "confirmed" else "⏳ Menunggu"
        lines.append(f"• {date_str} jam {time_str} ({r.guest_count} orang) — {status}")

    lines.append("\nKetik *batal* untuk membatalkan reservasi.")
    return "\n".join(lines)


async def handle_reservation_cancel(
    phone: str, outlet_id: str, db: AsyncSession, redis_client, **kwargs
) -> str:
    from backend.models.reservation import Reservation
    today = date.today()
    reservation = (await db.execute(
        select(Reservation).where(
            Reservation.outlet_id == outlet_id,
            Reservation.customer_phone == phone,
            Reservation.reservation_date >= today,
            Reservation.deleted_at.is_(None),
            Reservation.status.in_(["pending", "confirmed"]),
        ).order_by(Reservation.reservation_date.asc()).limit(1)
    )).scalar_one_or_none()

    if not reservation:
        return "Tidak ada reservasi aktif yang bisa dibatalkan."

    reservation.status = "cancelled"
    reservation.cancelled_at = datetime.now(timezone.utc)
    reservation.row_version += 1
    await db.commit()

    date_str = reservation.reservation_date.strftime("%d %B %Y") if reservation.reservation_date else "-"
    return f"❌ Reservasi Anda pada *{date_str}* telah dibatalkan.\n\nKetik *reservasi* untuk booking baru."


# ─── Conversation Flow Handlers ──────────────────────────────────────────────

def parse_date_input(text: str) -> Optional[date]:
    """Parse flexible date input."""
    msg = text.lower().strip()
    today = date.today()

    if msg in ("besok", "tomorrow"):
        return today + timedelta(days=1)
    if msg in ("lusa",):
        return today + timedelta(days=2)
    if msg in ("hari ini", "today"):
        return today

    # Try YYYY-MM-DD
    try:
        return datetime.strptime(msg, "%Y-%m-%d").date()
    except ValueError:
        pass

    # Try "15 April" or "15 april 2026"
    months_id = {
        "januari": 1, "februari": 2, "maret": 3, "april": 4,
        "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
        "september": 9, "oktober": 10, "november": 11, "desember": 12,
    }
    match = re.match(r"(\d{1,2})\s+(\w+)(?:\s+(\d{4}))?", msg)
    if match:
        day = int(match.group(1))
        month_name = match.group(2).lower()
        year = int(match.group(3)) if match.group(3) else today.year
        month = months_id.get(month_name)
        if month:
            try:
                result = date(year, month, day)
                if result < today:
                    result = date(year + 1, month, day)
                return result
            except ValueError:
                pass

    return None


def parse_time_input(text: str) -> Optional[time]:
    """Parse flexible time input."""
    msg = text.lower().strip()

    # "7 malam" → 19:00, "2 siang" → 14:00
    match = re.match(r"(\d{1,2})(?::(\d{2}))?\s*(pagi|siang|sore|malam)?", msg)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        period = match.group(3)

        if period == "malam" and hour < 12:
            hour += 12
        elif period == "sore" and hour < 12:
            hour += 12
        elif period == "siang" and hour < 12 and hour != 12:
            hour += 0  # 12 siang = 12
        elif period == "pagi" and hour == 12:
            hour = 0

        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return time(hour, minute)

    # Try HH:MM
    try:
        parts = msg.replace(".", ":").split(":")
        if len(parts) == 2:
            return time(int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        pass

    return None


def parse_guest_count(text: str) -> Optional[int]:
    """Parse guest count."""
    match = re.search(r"(\d+)", text)
    if match:
        count = int(match.group(1))
        if 1 <= count <= 50:
            return count
    return None


async def handle_conversation_flow(
    phone: str, message: str, outlet_id: str, outlet_name: str,
    redis_client, db: AsyncSession,
) -> str:
    """Handle multi-turn reservation conversation."""
    conv = await get_conversation(redis_client, phone, outlet_id)
    state = conv.get("state", STATE_IDLE)
    data = conv.get("data", {})

    if state == STATE_AWAITING_DATE:
        parsed = parse_date_input(message)
        if not parsed:
            return "Maaf, saya tidak mengerti tanggalnya. Coba format: *besok*, *lusa*, *15 April*, atau *2026-04-15*"
        if parsed < date.today():
            return "Tanggal sudah lewat. Pilih tanggal hari ini atau setelahnya."

        data["date"] = parsed.isoformat()
        conv["data"] = data
        conv["state"] = STATE_AWAITING_TIME
        await save_conversation(redis_client, phone, outlet_id, conv)

        date_str = parsed.strftime("%d %B %Y")
        return f"📅 Tanggal: *{date_str}*\n\nMau jam berapa?\nContoh: *19:00*, *7 malam*, *12:30*"

    elif state == STATE_AWAITING_TIME:
        parsed = parse_time_input(message)
        if not parsed:
            return "Maaf, format jamnya kurang tepat. Contoh: *19:00*, *7 malam*, *12 siang*"

        data["time"] = parsed.strftime("%H:%M")
        conv["data"] = data
        conv["state"] = STATE_AWAITING_GUESTS
        await save_conversation(redis_client, phone, outlet_id, conv)

        return f"🕐 Jam: *{data['time']}*\n\nUntuk berapa orang?"

    elif state == STATE_AWAITING_GUESTS:
        count = parse_guest_count(message)
        if not count:
            return "Berapa orang? Ketik angka, contoh: *4*"

        data["guests"] = count
        conv["data"] = data
        conv["state"] = STATE_AWAITING_NAME
        await save_conversation(redis_client, phone, outlet_id, conv)

        return f"👥 Jumlah tamu: *{count} orang*\n\nAtas nama siapa reservasinya?"

    elif state == STATE_AWAITING_NAME:
        name = message.strip()
        if len(name) < 2:
            return "Nama minimal 2 karakter. Atas nama siapa?"

        data["name"] = name
        conv["data"] = data
        conv["state"] = STATE_CONFIRM_BOOKING
        await save_conversation(redis_client, phone, outlet_id, conv)

        date_obj = date.fromisoformat(data["date"])
        date_str = date_obj.strftime("%d %B %Y")

        return (
            f"📝 *Konfirmasi Reservasi*\n\n"
            f"🏪 {outlet_name}\n"
            f"📅 {date_str}\n"
            f"🕐 {data['time']} WIB\n"
            f"👥 {data['guests']} orang\n"
            f"👤 Atas nama: {data['name']}\n\n"
            f"Ketik *ya* untuk konfirmasi atau *batal* untuk membatalkan."
        )

    elif state == STATE_CONFIRM_BOOKING:
        msg = message.lower().strip()
        if msg in ("ya", "yes", "ok", "oke", "konfirmasi", "confirm", "y"):
            # Execute booking
            result = await execute_reservation(
                phone=phone,
                outlet_id=outlet_id,
                outlet_name=outlet_name,
                res_date=date.fromisoformat(data["date"]),
                start_time=time.fromisoformat(data["time"] + ":00"),
                guest_count=data["guests"],
                customer_name=data["name"],
                db=db,
            )
            await clear_conversation(redis_client, phone, outlet_id)
            return result
        elif msg in ("batal", "cancel", "tidak", "no", "n"):
            await clear_conversation(redis_client, phone, outlet_id)
            return "❌ Reservasi dibatalkan. Ketik *reservasi* kapan saja untuk booking baru."
        else:
            return "Ketik *ya* untuk konfirmasi atau *batal* untuk membatalkan."

    return ""


async def execute_reservation(
    phone: str, outlet_id: str, outlet_name: str,
    res_date: date, start_time: time, guest_count: int,
    customer_name: str, db: AsyncSession,
) -> str:
    """Create reservation in DB."""
    from backend.models.reservation import Reservation, Table, ReservationSettings
    from backend.models.outlet import Outlet

    # Get settings
    settings_row = (await db.execute(
        select(ReservationSettings).where(ReservationSettings.outlet_id == outlet_id)
    )).scalar_one_or_none()

    if not settings_row or not settings_row.is_enabled:
        return "Maaf, reservasi belum tersedia untuk outlet ini."

    # Calculate end_time
    slot_minutes = settings_row.slot_duration_minutes or 120
    start_dt = datetime.combine(res_date, start_time)
    end_time = (start_dt + timedelta(minutes=slot_minutes)).time()

    # Check slot availability
    existing = (await db.execute(
        select(func.count(Reservation.id)).where(
            Reservation.outlet_id == outlet_id,
            Reservation.reservation_date == res_date,
            Reservation.deleted_at.is_(None),
            Reservation.status.in_(["pending", "confirmed", "seated"]),
            Reservation.start_time < end_time,
            Reservation.end_time > start_time,
        )
    )).scalar() or 0

    if existing >= settings_row.max_reservations_per_slot:
        return (
            f"Maaf, slot jam {start_time.strftime('%H:%M')} pada tanggal tersebut sudah penuh.\n"
            f"Coba waktu lain atau ketik *reservasi* untuk mulai ulang."
        )

    # Auto-assign table
    table = None
    tables_result = await db.execute(
        select(Table).where(
            Table.outlet_id == outlet_id,
            Table.deleted_at.is_(None),
            Table.is_active == True,
            Table.capacity >= guest_count,
        ).order_by(Table.capacity.asc())
    )
    for candidate in tables_result.scalars().all():
        conflict = (await db.execute(
            select(func.count(Reservation.id)).where(
                Reservation.table_id == candidate.id,
                Reservation.reservation_date == res_date,
                Reservation.deleted_at.is_(None),
                Reservation.status.in_(["pending", "confirmed", "seated"]),
                Reservation.start_time < end_time,
                Reservation.end_time > start_time,
            )
        )).scalar()
        if conflict == 0:
            table = candidate
            break

    # Determine status
    initial_status = "confirmed" if settings_row.auto_confirm else "pending"

    # Get tenant_id
    outlet = (await db.execute(select(Outlet).where(Outlet.id == outlet_id))).scalar_one_or_none()

    reservation = Reservation(
        outlet_id=outlet_id,
        tenant_id=outlet.tenant_id if outlet else None,
        table_id=table.id if table else None,
        reservation_date=res_date,
        start_time=start_time,
        end_time=end_time,
        guest_count=guest_count,
        customer_name=customer_name,
        customer_phone=phone,
        source="whatsapp",
        status=initial_status,
        confirmed_at=datetime.now(timezone.utc) if initial_status == "confirmed" else None,
    )
    db.add(reservation)
    await db.commit()

    date_str = res_date.strftime("%d %B %Y")
    time_str = start_time.strftime("%H:%M")
    end_str = end_time.strftime("%H:%M")
    table_info = f"🪑 Meja: {table.name}" if table else "🪑 Meja akan ditentukan"
    status_msg = "✅ Dikonfirmasi" if initial_status == "confirmed" else "⏳ Menunggu konfirmasi outlet"

    return (
        f"🎉 *Reservasi Berhasil!*\n\n"
        f"🏪 {outlet_name}\n"
        f"📅 {date_str}\n"
        f"🕐 {time_str} — {end_str} WIB\n"
        f"👥 {guest_count} orang\n"
        f"👤 {customer_name}\n"
        f"{table_info}\n"
        f"Status: {status_msg}\n\n"
        f"Kami tunggu kedatangannya! 🙏\n"
        f"Ketik *cek reservasi* untuk lihat status."
    )


# ─── AI Fallback (for ambiguous messages) ────────────────────────────────────

async def ai_compose_response(
    message: str, outlet_name: str, outlet_id: str, db: AsyncSession,
) -> Optional[str]:
    """Use Claude Haiku for ambiguous messages. Returns None if no API key."""
    if not settings.ANTHROPIC_API_KEY:
        return None

    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        # Get basic outlet info for context
        from backend.models.outlet import Outlet
        outlet = (await db.execute(select(Outlet).where(Outlet.id == outlet_id))).scalar_one_or_none()

        system = (
            f"Kamu adalah asisten WhatsApp untuk {outlet_name}, sebuah cafe di Indonesia. "
            f"Alamat: {outlet.address or '-'}. Jam buka: {outlet.opening_hours or '-'}. "
            f"Status: {'BUKA' if outlet.is_open else 'TUTUP'}. "
            f"Jawab singkat, ramah, dalam bahasa Indonesia. "
            f"Jika customer mau reservasi, arahkan ketik 'reservasi'. "
            f"Jika mau lihat menu, arahkan ketik 'menu'. "
            f"Max 3 kalimat."
        )

        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            system=system,
            messages=[{"role": "user", "content": message}],
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"AI compose error: {e}")
        return None


# ─── Main Handler ─────────────────────────────────────────────────────────────

async def handle_incoming_wa(
    phone: str, message: str, outlet_id: str, outlet_name: str,
    redis_client, db: AsyncSession,
) -> str:
    """
    Main entry point for incoming WhatsApp messages.
    Returns the response text to send back.
    """
    # Check if in active conversation flow
    conv = await get_conversation(redis_client, phone, outlet_id)
    if conv["state"] != STATE_IDLE:
        # Check for abort keywords
        if message.lower().strip() in ("batal", "cancel", "ulang", "reset"):
            await clear_conversation(redis_client, phone, outlet_id)
            return "🔄 Percakapan direset. Ada yang bisa saya bantu?"

        return await handle_conversation_flow(
            phone=phone, message=message, outlet_id=outlet_id,
            outlet_name=outlet_name, redis_client=redis_client, db=db,
        )

    # Classify intent
    intent = classify_wa_intent(message)

    if intent == "greeting":
        return await handle_greeting(outlet_name=outlet_name)

    elif intent == "menu_inquiry":
        return await handle_menu(outlet_id=outlet_id, db=db)

    elif intent == "general":
        return await handle_general(message=message, outlet_id=outlet_id, db=db)

    elif intent == "reservation_create":
        return await handle_reservation_start(
            phone=phone, outlet_id=outlet_id, outlet_name=outlet_name,
            redis_client=redis_client, db=db,
        )

    elif intent == "reservation_check":
        return await handle_reservation_check(phone=phone, outlet_id=outlet_id, db=db)

    elif intent == "reservation_cancel":
        return await handle_reservation_cancel(
            phone=phone, outlet_id=outlet_id, db=db, redis_client=redis_client,
        )

    elif intent == "unknown":
        # Try AI fallback
        ai_response = await ai_compose_response(
            message=message, outlet_name=outlet_name,
            outlet_id=outlet_id, db=db,
        )
        if ai_response:
            return ai_response

        return (
            f"Hai! Saya asisten *{outlet_name}* 😊\n\n"
            f"Beberapa hal yang bisa saya bantu:\n"
            f"• *menu* — lihat daftar menu\n"
            f"• *reservasi* — booking meja\n"
            f"• *cek reservasi* — cek status booking\n"
            f"• *jam buka* — info operasional"
        )

    return "Ada yang bisa saya bantu? 😊"
