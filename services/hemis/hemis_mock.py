"""
hemis_mock.py — Realistic Uzbek student mock data for demo/hackathon.

Set USE_HEMIS_MOCK=true in .env to activate automatically.
All public functions are importable directly:

    from services.hemis.hemis_mock import (
        MOCK_STUDENT,
        mock_get_attendance,
        mock_get_grades,
        mock_get_schedule,
        mock_get_today_missed,
    )
"""
from __future__ import annotations

from datetime import date, timedelta

# ─── Static student profile ───────────────────────────────────────────────────

MOCK_STUDENT: dict = {
    "hemis_id":     "S-20230147",
    "full_name":    "Toshmatov Jasurbek Anvarovich",
    "university":   "Toshkent Axborot Texnologiyalari Universiteti",
    "faculty":      "Dasturiy injiniring va axborot xavfsizligi",
    "specialty":    "Dasturiy ta'minot muhandisligi",
    "course":       2,
    "group":        "SE-22-05",
    "student_id":   "20231234567",
    "form":         "kunduzgi",
    "payment_form": "to'lov-shartnoma",
}


# ─── Subjects ─────────────────────────────────────────────────────────────────

_SUBJECTS: list[dict] = [
    {"name": "Matematika",            "nb_limit": 4, "teacher": "Rahimov B.T.",     "room_prefix": "A"},
    {"name": "Fizika",                "nb_limit": 4, "teacher": "Yusupova M.A.",    "room_prefix": "B"},
    {"name": "Ingliz tili",           "nb_limit": 4, "teacher": "Nazarova S.K.",    "room_prefix": "C"},
    {"name": "Dasturlash asoslari",   "nb_limit": 4, "teacher": "Karimov I.R.",     "room_prefix": "A"},
    {"name": "Iqtisodiyot",           "nb_limit": 4, "teacher": "Holiqov J.U.",     "room_prefix": "D"},
]

# nb_count deliberately chosen: 2 subjects near/at the danger threshold (≥2)
_SUBJECT_NB: dict[str, int] = {
    "Matematika":           1,
    "Fizika":               3,   # ← danger: 3/4
    "Ingliz tili":          2,   # ← warning: 2/4
    "Dasturlash asoslari":  0,
    "Iqtisodiyot":          2,   # ← warning: 2/4
}


# ─── 1. Attendance (last 30 calendar days, weekdays only) ─────────────────────

def mock_get_attendance() -> list[dict]:
    """
    Returns ≈30 attendance records spread over the last 30 days.
    Absences are distributed so Fizika, Ingliz tili and Iqtisodiyot
    have nb_count ≥ 2 to trigger demo alerts.
    """
    today = date.today()

    # Pre-planned absences keyed by (subject_name, days_ago)
    _planned_absences: set[tuple[str, int]] = {
        ("Fizika",       2),
        ("Fizika",       7),
        ("Fizika",      14),
        ("Ingliz tili",  3),
        ("Ingliz tili", 10),
        ("Iqtisodiyot",  5),
        ("Iqtisodiyot", 12),
    }

    records: list[dict] = []
    days_ago = 0
    subject_cycle = 0

    while days_ago <= 30 and len(records) < 30:
        check_date = today - timedelta(days=days_ago)
        if check_date.weekday() < 5:          # Monday–Friday only
            subj = _SUBJECTS[subject_cycle % len(_SUBJECTS)]
            name = subj["name"]
            nb_count = _SUBJECT_NB[name]

            is_absent = (name, days_ago) in _planned_absences
            status = "absent" if is_absent else "present"

            records.append({
                "subject":    name,
                "date":       check_date.isoformat(),
                "status":     status,
                "nb_count":   nb_count,
                "nb_limit":   subj["nb_limit"],
                "teacher":    subj["teacher"],
            })
            subject_cycle += 1
        days_ago += 1

    return records


# ─── 2. Grades ────────────────────────────────────────────────────────────────

def mock_get_grades() -> list[dict]:
    """
    One grade record per subject for the current semester.
    Grades reflect realistic performance variation.
    """
    _grades: dict[str, float | None] = {
        "Matematika":          78.5,
        "Fizika":              61.0,   # lower because of absences
        "Ingliz tili":         85.0,
        "Dasturlash asoslari": 92.5,
        "Iqtisodiyot":         None,   # not yet graded
    }

    return [
        {
            "subject":    subj["name"],
            "grade":      _grades[subj["name"]],
            "nb_count":   _SUBJECT_NB[subj["name"]],
            "nb_limit":   subj["nb_limit"],
            "semester":   2,
            "max_grade":  100.0,
            "teacher":    subj["teacher"],
            "graded":     _grades[subj["name"]] is not None,
        }
        for subj in _SUBJECTS
    ]


# ─── 3. Schedule (next 14 days, Mon–Sat) ─────────────────────────────────────

_TIME_SLOTS: list[str] = ["08:00", "09:30", "11:00", "13:00", "14:30", "16:00"]
_LESSON_TYPES: list[str] = ["lecture", "seminar", "practice", "lab"]

# Fixed weekly timetable: (weekday 0=Mon, subject_index, slot_index, lesson_type)
_WEEKLY_TIMETABLE: list[tuple[int, int, int, str]] = [
    (0, 0, 0, "lecture"),    # Mon  08:00  Matematika         lecture
    (0, 2, 1, "seminar"),    # Mon  09:30  Ingliz tili        seminar
    (0, 3, 2, "practice"),   # Mon  11:00  Dasturlash asoslari practice
    (1, 1, 0, "lecture"),    # Tue  08:00  Fizika             lecture
    (1, 4, 1, "seminar"),    # Tue  09:30  Iqtisodiyot        seminar
    (2, 0, 1, "seminar"),    # Wed  09:30  Matematika         seminar
    (2, 3, 2, "lab"),        # Wed  11:00  Dasturlash asoslari lab
    (3, 1, 1, "seminar"),    # Thu  09:30  Fizika             seminar
    (3, 2, 2, "practice"),   # Thu  11:00  Ingliz tili        practice
    (4, 4, 0, "lecture"),    # Fri  08:00  Iqtisodiyot        lecture
    (4, 0, 2, "practice"),   # Fri  11:00  Matematika         practice
    (5, 3, 0, "lab"),        # Sat  08:00  Dasturlash asoslari lab
]


def mock_get_schedule() -> list[dict]:
    """
    Returns schedule for the next 14 calendar days.
    Injects ONE exam 5 days from today (Fizika imtihoni) for deadline demo.
    """
    today = date.today()
    exam_date = today + timedelta(days=5)
    # Shift exam to next weekday if it falls on a weekend
    while exam_date.weekday() >= 5:
        exam_date += timedelta(days=1)

    records: list[dict] = []

    for delta in range(15):
        day = today + timedelta(days=delta)
        if day.weekday() > 5:
            continue
        for (weekday, subj_idx, slot_idx, ltype) in _WEEKLY_TIMETABLE:
            if day.weekday() != weekday:
                continue
            subj = _SUBJECTS[subj_idx]
            room_num = 100 + subj_idx * 11 + slot_idx
            records.append({
                "subject":     subj["name"],
                "date":        day.isoformat(),
                "time":        _TIME_SLOTS[slot_idx],
                "room":        f"{subj['room_prefix']}-{room_num}",
                "type":        ltype,
                "teacher":     subj["teacher"],
                "is_exam":     False,
            })

    # ── Inject the exam ──────────────────────────────────────────────────────
    records.append({
        "subject":     "Fizika",
        "date":        exam_date.isoformat(),
        "time":        "10:00",
        "room":        "B-210",
        "type":        "exam",
        "teacher":     "Yusupova M.A.",
        "is_exam":     True,
        "exam_note":   "Oraliq nazorat. Mavzular: Mexanika, Termodinamika, Optika",
    })

    records.sort(key=lambda r: (r["date"], r["time"]))
    return records


# ─── 4. Today's missed lessons ────────────────────────────────────────────────

def mock_get_today_missed() -> list[dict]:
    """
    Returns subjects the student missed today with study materials.
    Always returns 2 records so demo flows have something to act on.
    """
    return [
        {
            "subject":             "Ingliz tili",
            "topic":               "Present Perfect vs Past Simple — Advanced Usage",
            "teacher":             "Nazarova S.K.",
            "time":                "09:30",
            "room":                "C-105",
            "nb_count":            _SUBJECT_NB["Ingliz tili"],
            "nb_limit":            4,
            "materials_available": True,
            "materials": [
                {"title": "Present Perfect darslik bo'limi (PDF)", "url": "https://example.uz/en/pp.pdf"},
                {"title": "Video ma'ruza — YouTube",               "url": "https://youtube.com/watch?v=demo1"},
            ],
            "can_request_p2p":     True,
        },
        {
            "subject":             "Fizika",
            "topic":               "Termodinamikaning birinchi qonuni",
            "teacher":             "Yusupova M.A.",
            "time":                "08:00",
            "room":                "B-112",
            "nb_count":            _SUBJECT_NB["Fizika"],
            "nb_limit":            4,
            "materials_available": True,
            "materials": [
                {"title": "Termodinamika konspekti (DOCX)", "url": "https://example.uz/physics/thermo.docx"},
                {"title": "Masalalar to'plami (PDF)",        "url": "https://example.uz/physics/tasks.pdf"},
            ],
            "can_request_p2p":     True,
            "exam_in_days":        5,
            "exam_warning":        "⚠️ 5 kundan keyin oraliq nazorat!",
        },
    ]


# ─── 5. Danger subjects (nb_count ≥ nb_limit - 1) ────────────────────────────

def mock_get_danger_subjects() -> list[dict]:
    """
    Returns subjects where the student is 1–0 absence(s) away from the limit.
    Useful for notification triggers and dashboard warnings.
    """
    danger: list[dict] = []
    for subj in _SUBJECTS:
        nb = _SUBJECT_NB[subj["name"]]
        limit = subj["nb_limit"]
        remaining = limit - nb
        if remaining <= 2:
            danger.append({
                "subject":    subj["name"],
                "nb_count":   nb,
                "nb_limit":   limit,
                "remaining":  remaining,
                "risk_level": "critical" if remaining == 0 else "high" if remaining == 1 else "medium",
                "teacher":    subj["teacher"],
            })
    return danger
