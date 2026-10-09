import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import func, or_, select, text

from backend.models import AuditLog, HrAttendance, HrEmployee, HrSchedule, Outlet, User
from backend.schemas.access import HRIS_MANAGE
from backend.services.access import resolve_access


def now():
    return datetime.now(timezone.utc)


def tz(outlet):
    try:
        return ZoneInfo(outlet.timezone)
    except (ZoneInfoNotFoundError, TypeError):
        raise HTTPException(422, "Zona waktu outlet belum valid. Periksa pengaturan outlet.")


async def access(db, user, permission=None):
    context = await resolve_access(db, user)
    manager = context.allows(permission) if permission else any(context.allows(p) for p in HRIS_MANAGE)
    return manager, context.employee


async def require_manager(db, user, permission="hris.employees.manage"):
    context = await resolve_access(db, user)
    context.require(permission)
    return context


async def outlet(db, user, outlet_id):
    (await resolve_access(db, user)).require_outlet(outlet_id)
    result = await db.scalar(select(Outlet).where(Outlet.id == outlet_id, Outlet.tenant_id == user.tenant_id,
        Outlet.deleted_at.is_(None), Outlet.is_active.is_(True)))
    if not result:
        raise HTTPException(404, "Outlet aktif tidak ditemukan")
    tz(result)
    return result


async def employee_lock(db, user, employee_id):
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                     {"key": f"hr-employee:{user.tenant_id}:{employee_id}"})
    row = await db.scalar(select(HrEmployee).where(HrEmployee.id == employee_id,
        HrEmployee.tenant_id == user.tenant_id, HrEmployee.deleted_at.is_(None))
        .with_for_update().execution_options(populate_existing=True))
    if not row:
        raise HTTPException(404, "Karyawan tidak ditemukan")
    return row


def employment(employee, day, new=True):
    if new and not employee.is_active:
        raise HTTPException(409, "Karyawan sudah dinonaktifkan")
    if day < employee.started_on or (employee.ended_on and day > employee.ended_on):
        raise HTTPException(422, "Tanggal berada di luar masa kerja karyawan")


def version(row, body):
    if body.row_version != row.row_version:
        raise HTTPException(409, "Data sudah berubah. Tutup formulir lalu muat ulang sebelum mengedit.")


def employee_data(row, manager=True):
    return {"id": str(row.id), "code": row.code, "name": row.name, "position": row.position,
        "outlet_id": str(row.outlet_id), "user_id": str(row.user_id) if row.user_id else None,
        "phone": row.phone if manager else None, "started_on": row.started_on.isoformat(),
        "ended_on": row.ended_on.isoformat() if row.ended_on else None, "is_active": row.is_active,
        "notes": row.notes if manager else None, "row_version": row.row_version}


def record_data(row, employee_name=None):
    data = {"id": str(row.id), "employee_id": str(row.employee_id), "employee_name": employee_name,
        "outlet_id": str(row.outlet_id), "work_date": row.work_date.isoformat(), "row_version": row.row_version}
    if isinstance(row, HrSchedule):
        return {**data, "starts_at": row.starts_at.isoformat(), "ends_at": row.ends_at.isoformat(), "notes": row.notes}
    minutes = int((row.clock_out - row.clock_in).total_seconds() // 60) if row.clock_in and row.clock_out else None
    return {**data, "status": row.status, "clock_in": row.clock_in.isoformat() if row.clock_in else None,
        "clock_out": row.clock_out.isoformat() if row.clock_out else None, "reason": row.reason,
        "source": row.source, "minutes": minutes}


async def replay(db, user, body, action, entity_id):
    data = body.model_dump(mode="json")
    if data.get("account") is None:
        data.pop("account", None)
    encoded = json.dumps({"action": action, "entity_id": str(entity_id), "user": str(user.id),
        "body": data}, sort_keys=True).encode()
    if data.get("account"):
        from backend.core.config import settings
        fingerprint = hmac.new(settings.SECRET_KEY.encode(), encoded, hashlib.sha256).hexdigest()
    else:
        fingerprint = hashlib.sha256(encoded).hexdigest()
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                     {"key": f"hr-request:{user.tenant_id}:{body.client_request_id}"})
    prior = await db.scalar(select(AuditLog).where(AuditLog.tenant_id == user.tenant_id, AuditLog.entity == "hris",
        AuditLog.after_state["client_request_id"].astext == str(body.client_request_id)))
    if prior:
        if prior.after_state.get("fingerprint") != fingerprint:
            raise HTTPException(409, "Permintaan sudah dipakai dengan data berbeda")
        scope = prior.after_state.get("record", {}).get("outlet_id")
        if not scope:
            raise HTTPException(409, "Cakupan permintaan lama tidak tersedia. Muat ulang")
        (await resolve_access(db, user)).require_outlet(UUID(scope))
        return fingerprint, prior.after_state["result"]
    return fingerprint, None


async def finish(db, request, user, body, fingerprint, action, row, before=None, result_extra=None):
    await db.flush()
    result = {"id": str(row.id), "row_version": row.row_version, **(result_extra or {})}
    after = employee_data(row) if isinstance(row, HrEmployee) else record_data(row)
    db.add(AuditLog(tenant_id=user.tenant_id, user_id=user.id, action=action, entity="hris", entity_id=row.id,
        request_id=request.state.request_id, before_state=before, after_state={"client_request_id": str(body.client_request_id),
        "fingerprint": fingerprint, "result": result, "record": after, "voided": row.deleted_at is not None,
        "reason": getattr(body, "correction_reason", None) or getattr(body, "reason", None)}))
    await db.commit()
    return result


def validate_schedule(body, zone):
    if body.ends_at <= body.starts_at or body.ends_at - body.starts_at > timedelta(hours=24):
        raise HTTPException(422, "Jadwal harus berakhir setelah mulai, maksimal 24 jam")
    return body.starts_at.astimezone(zone).date()


def validate_attendance(body, zone, current=None, scheduled_window=None):
    current = current or now()
    if body.status == "hadir":
        if not body.clock_in:
            raise HTTPException(422, "Jam masuk wajib untuk status hadir")
        if body.clock_in.astimezone(zone).date() != body.work_date:
            in_night_schedule = scheduled_window and scheduled_window[0].astimezone(zone).date() == body.work_date and scheduled_window[0] <= body.clock_in < scheduled_window[1]
            if not in_night_schedule:
                raise HTTPException(422, "Jam masuk harus pada tanggal kerja atau dalam jadwal malam yang sesuai")
        if body.clock_in > current or (body.clock_out and body.clock_out > current):
            raise HTTPException(422, "Kehadiran tidak boleh dicatat di masa depan")
        if body.clock_out and body.clock_out < body.clock_in:
            raise HTTPException(422, "Jam pulang harus setelah jam masuk")
    elif body.clock_in or body.clock_out:
        raise HTTPException(422, "Izin, sakit, cuti, dan libur tidak memakai jam masuk/pulang")
    elif not body.reason:
        raise HTTPException(422, "Alasan wajib untuk izin, sakit, cuti, atau libur")


async def save_employee(db, request, user, body, employee_id=None):
    from backend.services import accounts, staff_accounts
    await accounts.lock(db, f"tenant:{user.tenant_id}")
    context = await require_manager(db, user)
    tenant = None
    if body.account:
        context, tenant = await staff_accounts.fresh_actor(db, request, user)
    action = "hr_employee_update" if employee_id else "hr_employee_create"
    fp, prior = await replay(db, user, body, action, employee_id)
    if prior:
        return prior
    await outlet(db, user, body.outlet_id)
    before = None
    if employee_id:
        row = await employee_lock(db, user, employee_id)
        context.require_outlet(row.outlet_id)
        version(row, body)
        before = employee_data(row)
        if row.user_id != body.user_id or row.outlet_id != body.outlet_id:
            opened = await db.scalar(select(HrAttendance.id).where(HrAttendance.tenant_id == user.tenant_id,
                HrAttendance.employee_id == row.id, HrAttendance.deleted_at.is_(None),
                HrAttendance.status == "hadir", HrAttendance.clock_out.is_(None)))
            if opened:
                raise HTTPException(409, "Catat pulang terlebih dahulu sebelum mengganti akun atau outlet penempatan")
    else:
        await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                         {"key": f"hr-code:{user.tenant_id}"})
        codes = (await db.scalars(select(HrEmployee.code).where(HrEmployee.tenant_id == user.tenant_id))).all()
        sequence = max([int(c.split("-")[1]) for c in codes if c.startswith("KRY-") and c[4:].isdigit()], default=0) + 1
        row = HrEmployee(id=uuid4(), tenant_id=user.tenant_id, code=f"KRY-{sequence:04d}", row_version=0)
        db.add(row)
    if context.mode == "managed" and row.user_id != body.user_id:
        context, tenant = await staff_accounts.fresh_actor(db, request, user)
        if row.user_id:
            await staff_accounts.target(db, user, context, row.user_id)
        if body.user_id:
            await staff_accounts.target(db, user, context, body.user_id, body.outlet_id)
    if body.user_id:
        linked = await db.scalar(select(User).where(User.id == body.user_id, User.tenant_id == user.tenant_id,
            User.deleted_at.is_(None)))
        if not linked or (not linked.is_active and row.user_id != body.user_id):
            raise HTTPException(404, "Akun kasir aktif tidak ditemukan dalam bisnis ini")
        if linked.is_superuser and row.user_id != body.user_id:
            raise HTTPException(403, "Akun pemilik tidak dapat ditautkan sebagai akun karyawan")
    if before and before["is_active"] and not body.is_active and row.user_id:
        from backend.services.accounts import revoke_all
        linked_account = await db.scalar(select(User).where(User.id == row.user_id,
            User.tenant_id == user.tenant_id, User.deleted_at.is_(None)).with_for_update())
        if linked_account and not linked_account.is_superuser:
            await revoke_all(db, linked_account)
    for key in ("name", "position", "outlet_id", "user_id", "phone", "started_on", "ended_on", "is_active", "notes"):
        setattr(row, key, getattr(body, key))
    row.row_version += 1
    result = await staff_accounts.configure(db, request, user, context, tenant, row, body.account) if body.account else None
    return await finish(db, request, user, body, fp, action, row, before, result)


async def remove_employee(db, request, user, body, employee_id):
    """Hapus karyawan oleh pemilik/pengelola (9 Okt 2026, permintaan Ivan).

    - Akun login karyawan dihapus lewat account_deletion.anonymize_user, rumah yang
      sama dengan "hapus akun saya": identitas dikosongkan, sesi dicabut, baris tetap
      (shifts/transaksi menunjuk user_id).
    - Profil karyawan disembunyikan (deleted_at) dan nomor HP dikosongkan. Nama dan
      kode tetap, karena riwayat jadwal/absensi menampilkan nama itu; query riwayat
      join ke profil tanpa filter deleted_at, jadi catatan lama tidak hilang.
    - Tidak bisa dibatalkan; antarmuka meminta konfirmasi dulu.
    """
    from backend.services import accounts, staff_accounts
    from backend.services.account_deletion import anonymize_user
    await accounts.lock(db, f"tenant:{user.tenant_id}")
    context = await require_manager(db, user)
    action = "hr_employee_remove"
    fp, prior = await replay(db, user, body, action, employee_id)
    if prior:
        return prior
    row = await employee_lock(db, user, employee_id)
    context.require_outlet(row.outlet_id)
    version(row, body)
    before = employee_data(row)
    opened = await db.scalar(select(HrAttendance.id).where(HrAttendance.tenant_id == user.tenant_id,
        HrAttendance.employee_id == row.id, HrAttendance.deleted_at.is_(None),
        HrAttendance.status == "hadir", HrAttendance.clock_out.is_(None)))
    if opened:
        raise HTTPException(409, "Catat pulang karyawan ini terlebih dahulu")
    account_removed = False
    if row.user_id:
        context, _ = await staff_accounts.fresh_actor(db, request, user)
        account = await staff_accounts.target(db, user, context, row.user_id)
        if account.id == user.id:
            raise HTTPException(403, "Akun sendiri dihapus lewat Akun saya")
        await anonymize_user(db, account)
        account_removed = True
    # Tanggal outlet, dan tidak sebelum tanggal mulai (karyawan yang belum sempat mulai).
    today = max(now().astimezone(tz(await db.get(Outlet, row.outlet_id))).date(), row.started_on)
    row.is_active = False
    row.ended_on = row.ended_on or today
    row.phone = None
    row.deleted_at = now()
    row.row_version += 1
    return await finish(db, request, user, body, fp, action, row, before, {"removed": True, "account_removed": account_removed})


async def request_status(db, user, client_request_id):
    context = await require_manager(db, user)
    prior = await db.scalar(select(AuditLog).where(AuditLog.tenant_id == user.tenant_id,
        AuditLog.user_id == user.id, AuditLog.entity == "hris",
        AuditLog.after_state["client_request_id"].astext == str(client_request_id)))
    if not prior:
        return {"state": "unknown"}
    context.require_outlet(UUID(prior.after_state["record"]["outlet_id"]))
    if prior.after_state["result"].get("account_configured"):
        context.require("hris.accounts.manage")
    return {"state": "saved", "result": prior.after_state["result"]}


async def get_record(db, user, model, record_id):
    row = await db.scalar(select(model).where(model.id == record_id, model.tenant_id == user.tenant_id,
        model.deleted_at.is_(None)))
    if not row:
        raise HTTPException(404, "Catatan tidak ditemukan")
    (await resolve_access(db, user)).require_outlet(row.outlet_id)
    return row


async def save_record(db, request, user, body, kind, record_id=None):
    context = await require_manager(db, user, "hris.schedules.manage" if kind == "schedule" else "hris.attendance.manage")
    model = HrSchedule if kind == "schedule" else HrAttendance
    action = f"hr_{kind}_{'update' if record_id else 'create'}"
    fp, prior = await replay(db, user, body, action, record_id)
    if prior:
        return prior
    # Lock the employee before loading a record so schedule and punch writes serialize together.
    employee = await employee_lock(db, user, body.employee_id)
    context.require_outlet(employee.outlet_id)
    out = await outlet(db, user, body.outlet_id)
    row, before = None, None
    if record_id:
        row = await get_record(db, user, model, record_id)
        await db.refresh(row)
        version(row, body)
        before = record_data(row)
        if row.employee_id != body.employee_id or row.outlet_id != body.outlet_id:
            raise HTTPException(422, "Karyawan dan outlet tidak bisa diganti. Batalkan catatan lalu buat yang benar.")
    if kind == "schedule":
        day = validate_schedule(body, tz(out))
        if row and row.work_date != day:
            raise HTTPException(422, "Tanggal jadwal tidak bisa diganti. Batalkan lalu buat jadwal yang benar.")
        employment(employee, day, new=row is None)
        if row:
            attended = await db.scalar(select(HrAttendance.id).where(HrAttendance.tenant_id == user.tenant_id,
                HrAttendance.employee_id == employee.id, HrAttendance.work_date == row.work_date,
                HrAttendance.deleted_at.is_(None)))
            if attended:
                raise HTTPException(409, "Jadwal sudah memiliki catatan kehadiran. Koreksi kehadirannya terlebih dahulu.")
        overlap = select(HrSchedule.id).where(HrSchedule.tenant_id == user.tenant_id,
            HrSchedule.employee_id == employee.id, HrSchedule.deleted_at.is_(None),
            HrSchedule.starts_at < body.ends_at, HrSchedule.ends_at > body.starts_at)
        if row:
            overlap = overlap.where(HrSchedule.id != row.id)
        if await db.scalar(overlap):
            raise HTTPException(409, "Waktu jadwal bertabrakan dengan jadwal karyawan ini")
        if not row:
            row = HrSchedule(tenant_id=user.tenant_id, employee_id=employee.id, outlet_id=out.id,
                             work_date=day, row_version=0)
            db.add(row)
        for key in ("starts_at", "ends_at", "notes"):
            setattr(row, key, getattr(body, key))
    else:
        scheduled_window = None
        if body.clock_in and body.clock_in.astimezone(tz(out)).date() != body.work_date:
            scheduled = await db.scalar(select(HrSchedule).where(HrSchedule.tenant_id == user.tenant_id,
                HrSchedule.employee_id == employee.id, HrSchedule.outlet_id == out.id,
                HrSchedule.work_date == body.work_date, HrSchedule.deleted_at.is_(None)))
            if scheduled:
                scheduled_window = (scheduled.starts_at, scheduled.ends_at)
        validate_attendance(body, tz(out), scheduled_window=scheduled_window)
        employment(employee, body.work_date, new=row is None)
        if row and row.work_date != body.work_date:
            raise HTTPException(422, "Tanggal kehadiran tidak bisa diganti. Batalkan lalu buat catatan yang benar.")
        if row and not body.correction_reason:
            raise HTTPException(422, "Alasan koreksi wajib diisi")
        if not row:
            row = HrAttendance(tenant_id=user.tenant_id, employee_id=employee.id, outlet_id=out.id,
                work_date=body.work_date, source="manual", recorded_by=user.id, row_version=0)
            db.add(row)
        for key in ("status", "clock_in", "clock_out", "reason"):
            setattr(row, key, getattr(body, key))
        row.updated_by = user.id
    row.row_version += 1
    return await finish(db, request, user, body, fp, action, row, before)


async def void_record(db, request, user, body, kind, record_id):
    await require_manager(db, user, "hris.schedules.manage" if kind == "schedule" else "hris.attendance.manage")
    action = f"hr_{kind}_void"
    fp, prior = await replay(db, user, body, action, record_id)
    if prior:
        return prior
    model = HrSchedule if kind == "schedule" else HrAttendance
    row = await get_record(db, user, model, record_id)
    await employee_lock(db, user, row.employee_id)
    await db.refresh(row)
    if row.deleted_at is not None:
        raise HTTPException(409, "Catatan sudah dibatalkan. Muat ulang.")
    version(row, body)
    if kind == "schedule" and await db.scalar(select(HrAttendance.id).where(HrAttendance.tenant_id == user.tenant_id,
        HrAttendance.employee_id == row.employee_id, HrAttendance.work_date == row.work_date,
        HrAttendance.deleted_at.is_(None))):
        raise HTTPException(409, "Jadwal sudah memiliki kehadiran. Batalkan kehadiran yang keliru terlebih dahulu.")
    before = record_data(row)
    row.deleted_at = now()
    row.row_version += 1
    if kind == "attendance":
        row.updated_by = user.id
    return await finish(db, request, user, body, fp, action, row, before)


async def punch(db, request, user, body):
    (await resolve_access(db, user)).require("hris.self")
    _, linked = await access(db, user)
    if not linked:
        raise HTTPException(403, "Akun ini belum terhubung ke profil karyawan. Minta pemilik menghubungkannya.")
    fp, prior = await replay(db, user, body, f"hr_punch_{body.action}", linked.id)
    if prior:
        return prior
    employee = await employee_lock(db, user, linked.id)
    if employee.user_id != user.id:
        raise HTTPException(403, "Hubungan akun karyawan sudah berubah. Muat ulang.")
    out = await outlet(db, user, body.outlet_id)
    current = now()
    opened = await db.scalar(select(HrAttendance).where(HrAttendance.tenant_id == user.tenant_id,
        HrAttendance.employee_id == employee.id, HrAttendance.deleted_at.is_(None),
        HrAttendance.status == "hadir", HrAttendance.clock_out.is_(None)))
    before = None
    if body.action == "out":
        if not opened:
            raise HTTPException(409, "Belum ada catatan masuk yang perlu ditutup")
        if opened.outlet_id != out.id:
            raise HTTPException(409, "Pilih outlet tempat kamu mencatat masuk")
        if current < opened.clock_in:
            raise HTTPException(409, "Jam masuk tercatat setelah waktu sekarang. Minta pengelola mengoreksinya.")
        row = opened
        before = record_data(row)
        row.clock_out = current
        row.updated_by = user.id
        row.row_version += 1
    else:
        if opened:
            raise HTTPException(409, "Masih ada catatan masuk yang belum ditutup. Catat pulang terlebih dahulu.")
        schedule = await db.scalar(select(HrSchedule).where(HrSchedule.tenant_id == user.tenant_id,
            HrSchedule.employee_id == employee.id, HrSchedule.outlet_id == out.id, HrSchedule.deleted_at.is_(None),
            HrSchedule.starts_at <= current, HrSchedule.ends_at > current))
        if out.id != employee.outlet_id and not schedule:
            raise HTTPException(403, "Pilih outlet penempatan atau outlet dengan jadwal kamu yang sedang berjalan")
        day = schedule.work_date if schedule else current.astimezone(tz(out)).date()
        employment(employee, day)
        row = HrAttendance(tenant_id=user.tenant_id, employee_id=employee.id, outlet_id=out.id, work_date=day,
            status="hadir", clock_in=current, source="self", recorded_by=user.id, updated_by=user.id, row_version=1)
        db.add(row)
    return await finish(db, request, user, body, fp, f"hr_punch_{body.action}", row, before)


async def setup(db, user):
    context = await resolve_access(db, user)
    manager = any(context.allows(p) for p in HRIS_MANAGE)
    if not manager:
        context.require("hris.self")
    employee = context.employee
    outlets = sorted(context.outlets, key=lambda o: (o.name, o.id))
    for out in outlets:
        tz(out)
    from backend.services.staff_accounts import options
    account_options = await options(db, user, context)
    open_record = await db.scalar(select(HrAttendance).where(HrAttendance.tenant_id == user.tenant_id,
        HrAttendance.employee_id == employee.id, HrAttendance.deleted_at.is_(None),
        HrAttendance.outlet_id.in_(context.outlet_ids), HrAttendance.status == "hadir",
        HrAttendance.clock_out.is_(None))) if employee and context.allows("hris.self") else None
    return {"is_manager": manager, "permissions": sorted(context.permissions & (HRIS_MANAGE | {"hris.self", "hris.accounts.manage", "access.manage"})),
        "access_version": context.version,
        "self_employee": employee_data(employee, False) if employee and context.allows("hris.self") else None,
        "open_attendance": record_data(open_record, employee.name) if open_record else None,
        "workspace_key": hashlib.sha256(f"{user.tenant_id}:{user.id}".encode()).hexdigest(),
        "outlets": [{"id": str(o.id), "name": o.name, "timezone": o.timezone} for o in outlets],
        **account_options, "generated_at": now().isoformat()}


async def workspace(db, user, outlet_id, start, end, kind, search, active, skip, limit):
    out = await outlet(db, user, outlet_id)
    if end < start or (end - start).days > 30:
        raise HTTPException(422, "Pilih periode 1 sampai 31 hari")
    context = await resolve_access(db, user)
    self_employee = context.employee
    managers = {HrEmployee: context.allows("hris.employees.manage"),
        HrSchedule: context.allows("hris.schedules.manage"), HrAttendance: context.allows("hris.attendance.manage")}
    model = {"employees": HrEmployee, "schedules": HrSchedule, "attendance": HrAttendance}[kind]
    manager = managers[model]
    if not manager:
        context.require("hris.self")
    scopes = {
        HrEmployee: [HrEmployee.tenant_id == user.tenant_id, HrEmployee.deleted_at.is_(None), HrEmployee.outlet_id == out.id],
        HrSchedule: [HrSchedule.tenant_id == user.tenant_id, HrSchedule.deleted_at.is_(None), HrSchedule.outlet_id == out.id,
                     HrSchedule.work_date >= start, HrSchedule.work_date <= end],
        HrAttendance: [HrAttendance.tenant_id == user.tenant_id, HrAttendance.deleted_at.is_(None), HrAttendance.outlet_id == out.id,
                       HrAttendance.work_date >= start, HrAttendance.work_date <= end]}
    for scoped_model in scopes:
        if not managers[scoped_model]:
            key = scoped_model.id if scoped_model == HrEmployee else scoped_model.employee_id
            scopes[scoped_model].append(key == (self_employee.id if self_employee and context.allows("hris.self") else None))
    count = lambda model, extra=(): db.scalar(select(func.count()).select_from(model).where(*scopes[model], *extra))
    active_count = await count(HrEmployee, [HrEmployee.is_active.is_(True)])
    scheduled = await count(HrSchedule)
    present = await count(HrAttendance, [HrAttendance.status == "hadir"])
    leave = await count(HrAttendance, [HrAttendance.status != "hadir"])
    open_count = await count(HrAttendance, [HrAttendance.status == "hadir", HrAttendance.clock_out.is_(None)])
    has_record = select(HrAttendance.id).where(HrAttendance.tenant_id == user.tenant_id,
        HrAttendance.employee_id == HrSchedule.employee_id, HrAttendance.work_date == HrSchedule.work_date,
        HrAttendance.outlet_id == HrSchedule.outlet_id, HrAttendance.deleted_at.is_(None)).exists()
    unrecorded = await db.scalar(select(func.count()).select_from(HrSchedule).where(*scopes[HrSchedule],
        HrSchedule.starts_at <= now(), ~has_record)) if managers[HrSchedule] == managers[HrAttendance] and (
            managers[HrSchedule] or context.allows("hris.self")) else None
    model = {"employees": HrEmployee, "schedules": HrSchedule, "attendance": HrAttendance}[kind]
    filters = list(scopes[model])
    if kind == "employees" and active:
        filters.append(HrEmployee.is_active.is_(active == "active"))
    query = select(model)
    if model != HrEmployee:
        query = query.join(HrEmployee, (HrEmployee.id == model.employee_id) & (HrEmployee.tenant_id == model.tenant_id))
    if search:
        term = "%" + search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        filters.append(or_(HrEmployee.name.ilike(term, escape="\\"), HrEmployee.code.ilike(term, escape="\\")))
    total = await db.scalar(select(func.count()).select_from(query.where(*filters).subquery()))
    ordering = [HrEmployee.name, HrEmployee.id] if model == HrEmployee else [model.work_date.desc(), model.id]
    rows = (await db.scalars(query.where(*filters).order_by(*ordering).offset(skip).limit(limit))).all()
    if model == HrEmployee:
        items = [employee_data(row, manager) for row in rows]
    else:
        ids = {row.employee_id for row in rows}
        names = dict((await db.execute(select(HrEmployee.id, HrEmployee.name).where(HrEmployee.tenant_id == user.tenant_id,
            HrEmployee.id.in_(ids)))).all()) if ids else {}
        items = [record_data(row, names.get(row.employee_id)) for row in rows]
    return {"items": items, "total": total, "skip": skip, "limit": limit, "kind": kind,
        "summary": {"active_employees": active_count if managers[HrEmployee] or context.allows("hris.self") else None,
                    "scheduled": scheduled if managers[HrSchedule] or context.allows("hris.self") else None,
                    "present": present if managers[HrAttendance] or context.allows("hris.self") else None,
                    "leave": leave if managers[HrAttendance] or context.allows("hris.self") else None,
                    "open": open_count if managers[HrAttendance] or context.allows("hris.self") else None,
                    "unrecorded_started": unrecorded},
        "summary_scopes": {label: "outlet_period" if managers[model] else "self_outlet_period" if context.allows("hris.self") else "no_access"
            for label, model in (("employees", HrEmployee), ("schedules", HrSchedule), ("attendance", HrAttendance))},
        "outlet_id": str(out.id), "timezone": out.timezone, "start": start.isoformat(), "end": end.isoformat(),
        "scope": "outlet_period" if manager else "self_outlet_period", "basis": "recorded_attendance_and_schedules",
        "generated_at": now().isoformat()}


async def employee_choices(db, user, search, skip, limit):
    context = await resolve_access(db, user)
    if not any(context.allows(p) for p in HRIS_MANAGE):
        raise HTTPException(403, "Akses daftar karyawan belum diberikan")
    filters = [HrEmployee.tenant_id == user.tenant_id, HrEmployee.deleted_at.is_(None), HrEmployee.is_active.is_(True),
        HrEmployee.outlet_id.in_(context.outlet_ids)]
    if search:
        term = "%" + search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        filters.append(or_(HrEmployee.name.ilike(term, escape="\\"), HrEmployee.code.ilike(term, escape="\\")))
    total = await db.scalar(select(func.count()).select_from(HrEmployee).where(*filters))
    rows = (await db.scalars(select(HrEmployee).where(*filters).order_by(HrEmployee.name, HrEmployee.id)
                             .offset(skip).limit(limit))).all()
    return {"items": [{"id": str(r.id), "name": r.name, "code": r.code} for r in rows], "total": total}
