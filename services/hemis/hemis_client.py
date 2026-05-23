"""
HEMIS API client.

All public methods return typed dicts and transparently fall back to
hemis_mock.py when HEMIS is unreachable or USE_HEMIS_MOCK=true.
"""
from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta
from typing import Any, TypedDict

import httpx
from loguru import logger

from core.config import settings
from services.hemis.hemis_auth import HEMISUnavailableError
from services.hemis import hemis_mock as _mock

# ─── Base URL ─────────────────────────────────────────────────────────────────

API_BASE = "https://student.hemis.uz/rest/v1"
_TIMEOUT = httpx.Timeout(15.0)


# ─── Return types ─────────────────────────────────────────────────────────────

class StudentInfo(TypedDict):
    hemis_id: str
    full_name: str
    university: str
    faculty: str
    course: int
    specialty: str
    student_status: str


class AttendanceRecord(TypedDict):
    subject: str
    date: str          # ISO date
    status: str        # present | absent | excused


class GradeRecord(TypedDict):
    subject: str
    grade: float | None
    nb_count: int      # number of absences (naposeshchaemost)
    max_grade: float
    semester: int


class ScheduleRecord(TypedDict):
    subject: str
    date: str          # ISO date
    time: str          # HH:MM
    lesson_type: str   # lecture | seminar | lab | practice
    room: str
    teacher: str


# ─── Client ───────────────────────────────────────────────────────────────────

class HEMISClient:
    """
    Async HEMIS REST API client.

    Usage:
        async with HEMISClient(access_token="…") as client:
            info = await client.get_student_info()
    """

    def __init__(self, access_token: str, *, use_mock: bool | None = None):
        self._token = access_token
        self._use_mock: bool = (
            use_mock
            if use_mock is not None
            else getattr(settings, "USE_HEMIS_MOCK", False)
        )
        self._http: httpx.AsyncClient | None = None

    # ── Context manager ──────────────────────────────────────────────────────

    async def __aenter__(self) -> "HEMISClient":
        self._http = httpx.AsyncClient(
            base_url=API_BASE,
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=_TIMEOUT,
        )
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._http:
            await self._http.aclose()

    # ── Public API ────────────────────────────────────────────────────────────

    async def get_student_info(self) -> StudentInfo:
        """Return basic student profile from HEMIS."""
        if self._use_mock:
            return _mock_student_info()
        data = await self._get("/account/me")
        return _parse_student_info(data)

    async def get_attendance(self) -> list[AttendanceRecord]:
        """Return attendance records for the current semester."""
        if self._use_mock:
            return _mock_attendance()
        data = await self._get("/education/attendance")
        return _parse_attendance(data)

    async def get_grades(self) -> list[GradeRecord]:
        """Return grade + nb_count per subject for the current semester."""
        if self._use_mock:
            return _mock_grades()
        data = await self._get("/education/performance")
        return _parse_grades(data)

    async def get_schedule(self) -> list[ScheduleRecord]:
        """Return upcoming schedule for the next 14 days."""
        if self._use_mock:
            return _mock_schedule()
        data = await self._get("/education/schedule")
        return _parse_schedule(data)

    # ── Internal ─────────────────────────────────────────────────────────────

    async def _get(self, path: str, **params: Any) -> Any:
        if self._http is None:
            raise RuntimeError("Use HEMISClient as an async context manager.")
        try:
            response = await self._http.get(path, params=params or None)
            if response.status_code == 401:
                from services.hemis.hemis_auth import HEMISAuthError
                raise HEMISAuthError("Access token rejected by HEMIS")
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as exc:
            logger.warning("HEMIS timeout on {}: {}", path, exc)
            raise HEMISUnavailableError(f"HEMIS timed out: {path}") from exc
        except httpx.RequestError as exc:
            logger.warning("HEMIS request error on {}: {}", path, exc)
            raise HEMISUnavailableError(f"HEMIS unreachable: {path}") from exc


# ─── Response parsers ─────────────────────────────────────────────────────────

def _parse_student_info(data: dict) -> StudentInfo:
    d = data.get("data", data)
    return StudentInfo(
        hemis_id=str(d.get("student_id_number", d.get("hemis_id", ""))),
        full_name=d.get("full_name", ""),
        university=d.get("university", {}).get("name", d.get("university", "")),
        faculty=d.get("faculty", {}).get("name", d.get("faculty", "")),
        course=int(d.get("level", {}).get("name", d.get("course", 1))),
        specialty=d.get("specialty", {}).get("name", d.get("specialty", "")),
        student_status=d.get("studentStatus", {}).get("name", "active"),
    )


def _parse_attendance(data: dict) -> list[AttendanceRecord]:
    records = data.get("data", data) if isinstance(data, dict) else data
    result: list[AttendanceRecord] = []
    for r in records:
        result.append(
            AttendanceRecord(
                subject=r.get("subject", {}).get("name", r.get("subject", "")),
                date=r.get("date", ""),
                status=r.get("attend_status", {}).get("name", r.get("status", "present")).lower(),
            )
        )
    return result


def _parse_grades(data: dict) -> list[GradeRecord]:
    records = data.get("data", data) if isinstance(data, dict) else data
    result: list[GradeRecord] = []
    for r in records:
        result.append(
            GradeRecord(
                subject=r.get("subject", {}).get("name", r.get("subject", "")),
                grade=float(r["grade"]) if r.get("grade") is not None else None,
                nb_count=int(r.get("nb_count", r.get("absentHours", 0))),
                max_grade=float(r.get("max_grade", 100)),
                semester=int(r.get("semester", {}).get("id", r.get("semester", 1))),
            )
        )
    return result


def _parse_schedule(data: dict) -> list[ScheduleRecord]:
    records = data.get("data", data) if isinstance(data, dict) else data
    result: list[ScheduleRecord] = []
    for r in records:
        lesson_date = r.get("date", r.get("lesson_date", ""))
        lesson_time = r.get("trainingTime", {}).get("name", r.get("time", "08:00"))
        # Normalise "HH:MM-HH:MM" → "HH:MM"
        lesson_time = lesson_time.split("-")[0].strip()
        result.append(
            ScheduleRecord(
                subject=r.get("subject", {}).get("name", r.get("subject", "")),
                date=lesson_date,
                time=lesson_time,
                lesson_type=r.get("lessonType", {}).get("name", r.get("lesson_type", "lecture")).lower(),
                room=r.get("auditorium", {}).get("name", r.get("room", "—")),
                teacher=r.get("employee", {}).get("name", r.get("teacher", "—")),
            )
        )
    return result


# ─── Mock delegates (single source of truth: hemis_mock.py) ──────────────────

def _mock_student_info() -> StudentInfo:
    d = _mock.MOCK_STUDENT
    return StudentInfo(
        hemis_id=d["hemis_id"],
        full_name=d["full_name"],
        university=d["university"],
        faculty=d["faculty"],
        course=d["course"],
        specialty=d["specialty"],
        student_status="active",
    )


def _mock_attendance() -> list[AttendanceRecord]:
    return [
        AttendanceRecord(
            subject=r["subject"],
            date=r["date"],
            status=r["status"],
        )
        for r in _mock.mock_get_attendance()
    ]


def _mock_grades() -> list[GradeRecord]:
    return [
        GradeRecord(
            subject=r["subject"],
            grade=r["grade"],
            nb_count=r["nb_count"],
            max_grade=r["max_grade"],
            semester=r["semester"],
        )
        for r in _mock.mock_get_grades()
    ]


def _mock_schedule() -> list[ScheduleRecord]:
    return [
        ScheduleRecord(
            subject=r["subject"],
            date=r["date"],
            time=r["time"],
            lesson_type=r["type"],
            room=r["room"],
            teacher=r["teacher"],
        )
        for r in _mock.mock_get_schedule()
    ]


# ─── Convenience factory ──────────────────────────────────────────────────────

def make_hemis_client(access_token: str) -> HEMISClient:
    """
    Factory that respects USE_HEMIS_MOCK env flag.

    If the token is empty / settings dictate mock mode, mock is enabled
    so the app stays functional during demos without HEMIS credentials.
    """
    force_mock = not access_token or getattr(settings, "USE_HEMIS_MOCK", False)
    if force_mock:
        logger.warning("HEMISClient: running in MOCK mode")
    return HEMISClient(access_token=access_token, use_mock=force_mock)
