from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.core.database import get_db
from backend.models import User
from backend.schemas.hris import AttendanceSave, EmployeeSave, Punch, ScheduleSave, VoidRecord
from backend.schemas.response import StandardResponse
from backend.services import hris as svc

router = APIRouter()


def response(request, data, message=None):
    return StandardResponse(success=True, data=data, message=message, request_id=request.state.request_id)


async def write(request, db, coroutine, message):
    try:
        return response(request, await coroutine, message)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Sudah ada catatan pada tanggal ini, akun sudah terhubung, atau data terkait berubah. Muat ulang.")


@router.get("/setup")
async def setup(request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return response(request, await svc.setup(db, user))


@router.get("/workspace")
async def workspace(request: Request, outlet_id: UUID, start: date, end: date,
    kind: Literal["employees", "schedules", "attendance"] = "employees", search: str = Query("", max_length=120),
    active: Literal["", "active", "inactive"] = "", skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return response(request, await svc.workspace(db, user, outlet_id, start, end, kind, search, active, skip, limit))


@router.get("/requests/{client_request_id}")
async def request_status(client_request_id: UUID, request: Request,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return response(request, await svc.request_status(db, user, client_request_id))


@router.get("/employee-choices")
async def choices(request: Request, search: str = Query("", max_length=120), skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100), db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return response(request, await svc.employee_choices(db, user, search, skip, limit))


@router.post("/employees")
async def create_employee(body: EmployeeSave, request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await write(request, db, svc.save_employee(db, request, user, body), "Profil karyawan disimpan")


@router.put("/employees/{employee_id}")
async def edit_employee(employee_id: UUID, body: EmployeeSave, request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await write(request, db, svc.save_employee(db, request, user, body, employee_id), "Profil karyawan diperbarui")


@router.post("/schedules")
async def create_schedule(body: ScheduleSave, request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await write(request, db, svc.save_record(db, request, user, body, "schedule"), "Jadwal disimpan")


@router.put("/schedules/{record_id}")
async def edit_schedule(record_id: UUID, body: ScheduleSave, request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await write(request, db, svc.save_record(db, request, user, body, "schedule", record_id), "Jadwal diperbarui")


@router.post("/schedules/{record_id}/void")
async def cancel_schedule(record_id: UUID, body: VoidRecord, request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await write(request, db, svc.void_record(db, request, user, body, "schedule", record_id), "Jadwal dibatalkan")


@router.post("/attendance")
async def create_attendance(body: AttendanceSave, request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await write(request, db, svc.save_record(db, request, user, body, "attendance"), "Kehadiran disimpan")


@router.put("/attendance/{record_id}")
async def edit_attendance(record_id: UUID, body: AttendanceSave, request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await write(request, db, svc.save_record(db, request, user, body, "attendance", record_id), "Kehadiran dikoreksi")


@router.post("/attendance/{record_id}/void")
async def void_attendance(record_id: UUID, body: VoidRecord, request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await write(request, db, svc.void_record(db, request, user, body, "attendance", record_id), "Catatan kehadiran dibatalkan")


@router.post("/punch")
async def punch(body: Punch, request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await write(request, db, svc.punch(db, request, user, body), "Kehadiran masuk/pulang disimpan")
