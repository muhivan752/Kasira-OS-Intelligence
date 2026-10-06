import unittest
from datetime import date, datetime, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from pydantic import ValidationError

from backend.schemas.hris import AttendanceSave, EmployeeSave, ScheduleSave
from backend.services.hris import validate_attendance, validate_schedule


class HrisValidationTests(unittest.TestCase):
    def test_employment_dates_and_names(self):
        fields = dict(client_request_id=uuid4(), outlet_id=uuid4(), name="QA", position="Kasir", started_on=date(2026, 1, 1))
        for changes in ({"name": " "}, {"position": " "}, {"ended_on": date(2025, 1, 1)}, {"unknown": True}):
            with self.assertRaises(ValidationError):
                EmployeeSave(**{**fields, **changes})

    def test_schedule_overnight_and_outlet_day(self):
        body = ScheduleSave(client_request_id=uuid4(), employee_id=uuid4(), outlet_id=uuid4(),
            starts_at="2026-10-01T16:00:00Z", ends_at="2026-10-02T00:00:00Z")
        self.assertEqual(validate_schedule(body, ZoneInfo("Asia/Jakarta")), date(2026, 10, 1))
        self.assertEqual(validate_schedule(body, ZoneInfo("Asia/Jayapura")), date(2026, 10, 2))
        for end in ("2026-10-01T15:00:00Z", "2026-10-03T00:00:00Z"):
            with self.assertRaises(HTTPException):
                validate_schedule(body.model_copy(update={"ends_at": datetime.fromisoformat(end)}), ZoneInfo("Asia/Jakarta"))
        with self.assertRaises(ValidationError):
            ScheduleSave(**{**body.model_dump(), "starts_at": datetime(2026, 10, 1)})

    def test_presence_leave_and_future_times(self):
        body = AttendanceSave(client_request_id=uuid4(), employee_id=uuid4(), outlet_id=uuid4(),
            work_date="2026-10-01", status="hadir", clock_in="2026-10-01T16:00:00Z", clock_out="2026-10-02T00:00:00Z")
        current = datetime(2026, 10, 3, tzinfo=timezone.utc)
        validate_attendance(body, ZoneInfo("Asia/Jakarta"), current)
        for changes in ({"clock_in": None}, {"clock_out": datetime(2026, 10, 4, tzinfo=timezone.utc)}, {"work_date": date(2026, 10, 2)}, {"status": "izin"}):
            with self.assertRaises(HTTPException):
                validate_attendance(body.model_copy(update=changes), ZoneInfo("Asia/Jakarta"), current)
        leave = body.model_copy(update={"status": "cuti", "clock_in": None, "clock_out": None, "reason": "Dikonfirmasi"})
        validate_attendance(leave, ZoneInfo("Asia/Jakarta"), current)
        with self.assertRaises(HTTPException):
            validate_attendance(leave.model_copy(update={"reason": None}), ZoneInfo("Asia/Jakarta"), current)

    def test_after_midnight_clock_in_uses_its_night_schedule(self):
        body = AttendanceSave(client_request_id=uuid4(), employee_id=uuid4(), outlet_id=uuid4(),
            work_date="2026-10-06", status="hadir", clock_in="2026-10-06T17:30:00Z")
        window = (datetime.fromisoformat("2026-10-06T16:00:00Z"), datetime.fromisoformat("2026-10-07T00:00:00Z"))
        current = datetime(2026, 10, 7, 1, tzinfo=timezone.utc)
        validate_attendance(body, ZoneInfo("Asia/Jakarta"), current, window)
        for other_window in (None, (window[0], window[0]), (current, current)):
            with self.assertRaises(HTTPException):
                validate_attendance(body, ZoneInfo("Asia/Jakarta"), current, other_window)
