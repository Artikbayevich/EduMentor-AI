"""
bot/messages.py — All user-facing text templates.

Centralised here so copy changes never require touching handler logic.
All strings are in Uzbek (with emoji).
"""
from __future__ import annotations

from services.nb_service import NBStatus, MissedLesson, Deadline, RiskLevel


# ─── Symbols ─────────────────────────────────────────────────────────────────

_RISK_ICON = {
    RiskLevel.LOW:      "🟢",
    RiskLevel.MEDIUM:   "🟡",
    RiskLevel.HIGH:     "🟠",
    RiskLevel.CRITICAL: "🔴",
}

_LESSON_TYPE_ICON = {
    "lecture":  "📖",
    "seminar":  "💬",
    "lab":      "🔬",
    "practice": "⚙️",
    "exam":     "📝",
}


# ─── Welcome / auth ───────────────────────────────────────────────────────────

WELCOME = (
    "👋 Assalomu alaykum! Men <b>EduMentor AI</b> — aqlli o'quv yordamchingizman.\n\n"
    "🎓 HEMIS tizimiga ulaning va men sizga:\n"
    "  • Dars qoldirishlarni kuzataman\n"
    "  • Imtihon muddatlarini eslataman\n"
    "  • Tushunmagan mavzular bo'yicha yordam topaman\n\n"
    "Boshlash uchun HEMIS hisobingizga kiring 👇"
)

ALREADY_LOGGED_IN = (
    "✅ Siz allaqachon tizimga kirgansiz!\n\n"
    "Quyidagi buyruqlardan foydalaning:"
)

AUTH_PENDING = (
    "🔗 HEMIS sahifasi ochildi.\n\n"
    "Kirgandan so'ng bot avtomatik faollashadi.\n"
    "Muammo bo'lsa /start ni qayta bosing."
)

AUTH_SUCCESS = (
    "✅ <b>Muvaffaqiyatli ulandi!</b>\n\n"
    "Xush kelibsiz, <b>{full_name}</b>! 🎉\n"
    "🏫 {university}\n"
    "📚 {faculty} — {course}-kurs\n\n"
    "Endi /status bilan boshla!"
)

AUTH_FAILED = (
    "❌ Autentifikatsiya muvaffaqiyatsiz.\n"
    "Iltimos, qayta urinib ko'ring: /start"
)

NOT_AUTHENTICATED = (
    "🔒 Bu funksiyadan foydalanish uchun avval tizimga kiring.\n"
    "👉 /start"
)


# ─── Help ─────────────────────────────────────────────────────────────────────

HELP = (
    "📖 <b>EduMentor AI bot — qo'llanma</b>\n\n"
    "<b>Buyruqlar:</b>\n"
    "  /start     — Botni ishga tushirish / kirish\n"
    "  /status    — Bugungi jadval va NB xulosa\n"
    "  /nb        — Fan bo'yicha NB holati\n"
    "  /deadlines — Yaqin 7 kunlik imtihon va topshiriqlar\n"
    "  /help      — Ushbu yordam xabari\n\n"
    "<b>Xabarlar:</b>\n"
    "  Bot dars qoldirganda avtomatik xabar yuboradi.\n"
    "  Barcha materiallar va testlar veb-saytda mavjud.\n\n"
    "🌐 <a href='{website_url}'>EduMentor AI platformasi</a>"
)


# ─── Status ───────────────────────────────────────────────────────────────────

def format_status(
    full_name: str,
    today_schedule: list[dict],
    nb_statuses: list[NBStatus],
    website_url: str,
) -> str:
    lines = [f"📊 <b>Bugungi holat</b> — {full_name}\n"]

    # Today's schedule
    if today_schedule:
        lines.append("🕐 <b>Bugungi darslar:</b>")
        for lesson in today_schedule[:5]:
            icon = _LESSON_TYPE_ICON.get(lesson.get("type", ""), "📌")
            lines.append(
                f"  {icon} {lesson['time']} — {lesson['subject']}"
                f"  ({lesson.get('room', '—')})"
            )
    else:
        lines.append("✅ Bugun dars yo'q yoki ma'lumot topilmadi.")

    # NB quick summary
    lines.append("\n⚠️ <b>NB xulosa:</b>")
    if not nb_statuses:
        lines.append("  ✅ Barcha fanlarda NB yo'q.")
    else:
        danger = [s for s in nb_statuses if s.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)]
        if not danger:
            lines.append("  ✅ Xavfli NB holati yo'q.")
        else:
            for s in danger[:4]:
                icon = _RISK_ICON[s.risk_level]
                lines.append(
                    f"  {icon} {s.subject}: {s.current_nb}/{s.max_nb}"
                    f" ({s.remaining} ta qoldi)"
                )

    lines.append(f"\n🌐 <a href='{website_url}/dashboard'>To'liq hisobot</a>")
    return "\n".join(lines)


# ─── NB detail ────────────────────────────────────────────────────────────────

def format_nb_list(nb_statuses: list[NBStatus], website_url: str) -> str:
    if not nb_statuses:
        return "✅ Hozircha NB qayd etilmagan. Zo'r!\n\n🌐 " + website_url

    lines = ["📊 <b>Fan bo'yicha NB holati</b>\n"]
    for s in nb_statuses:
        icon = _RISK_ICON[s.risk_level]
        bar  = _progress_bar(s.current_nb, s.max_nb)
        lines.append(
            f"{icon} <b>{s.subject}</b>\n"
            f"   {bar}  {s.current_nb}/{s.max_nb} NB"
            f"  <i>({s.remaining} ta qoldi)</i>\n"
        )
    lines.append(f"🌐 <a href='{website_url}/nb'>Batafsil</a>")
    return "\n".join(lines)


def format_nb_alert(missed: MissedLesson, website_url: str, lesson_id: str) -> str:
    """
    Auto-notification sent when an absence is detected.
    Matches the exact format specified in the brief.
    """
    return (
        f"⚠️ <b>{missed.subject}</b> fanidan bugun dars qoldirildi\n\n"
        f"📚 Mavzu: {missed.topic}\n"
        f"📊 NB holati: {missed.nb_count}/{missed.nb_limit} "
        f"({'🔴' if missed.nb_limit - missed.nb_count <= 1 else '🟠'} "
        f"{missed.nb_limit - missed.nb_count} ta qoldi)\n\n"
        f"→ Konspekt va testni ko'rish: "
        f"{website_url}/lesson/{lesson_id}"
    )


# ─── Deadlines ────────────────────────────────────────────────────────────────

def format_deadlines(deadlines: list[Deadline], website_url: str) -> str:
    if not deadlines:
        return (
            "✅ Yaqin 7 kunda imtihon yoki muhim topshiriq yo'q.\n\n"
            f"🌐 <a href='{website_url}/schedule'>To'liq jadval</a>"
        )

    lines = ["📅 <b>Yaqin 7 kunda:</b>\n"]
    for d in deadlines:
        icon = "📝" if d.is_exam else _LESSON_TYPE_ICON.get(d.type, "📌")
        urgency = "❗" if d.days_away <= 2 else ("⚡" if d.days_away <= 4 else "")
        days_txt = (
            "Bugun!" if d.days_away == 0
            else f"{d.days_away} kun qoldi"
        )
        lines.append(
            f"{urgency}{icon} <b>{d.subject}</b>\n"
            f"   📆 {d.date}  🕐 {d.time}  🚪 {d.room}\n"
            f"   ⏳ {days_txt}"
        )
        if d.note:
            lines.append(f"   📝 {d.note}")
        lines.append("")

    lines.append(f"🌐 <a href='{website_url}/schedule'>To'liq jadval</a>")
    return "\n".join(lines)


# ─── P2P ─────────────────────────────────────────────────────────────────────

def format_p2p_request_sent(subject: str, coin_offer: int) -> str:
    return (
        f"✅ <b>P2P so'rov yuborildi!</b>\n\n"
        f"📚 Fan: {subject}\n"
        f"💰 Taklif: {coin_offer} coin\n\n"
        f"Mos yordam beruvchi topilganda sizga xabar yuboriladi."
    )


def format_p2p_match_found(helper_name: str, subject: str, request_id: str) -> str:
    return (
        f"🤝 <b>Mos yordam beruvchi topildi!</b>\n\n"
        f"👤 {helper_name}\n"
        f"📚 Fan: {subject}\n\n"
        f"Qabul qilasizmi?"
    )


def format_p2p_new_request(requester_name: str, subject: str, description: str, coin_offer: int) -> str:
    return (
        f"🔔 <b>Yangi yordam so'rovi!</b>\n\n"
        f"👤 {requester_name}\n"
        f"📚 Fan: {subject}\n"
        f"💬 {description}\n"
        f"💰 Taklif: {coin_offer} coin\n\n"
        f"Yordam bera olasizmi?"
    )


# ─── Leaderboard ──────────────────────────────────────────────────────────────

def format_leaderboard_entry(
    rank_national: int | None,
    rank_university: int | None,
    total_coins: float,
    full_name: str,
) -> str:
    return (
        f"🏆 <b>Reyting</b>\n\n"
        f"👤 {full_name}\n"
        f"💰 Jami coin: <b>{total_coins:.0f}</b>\n"
        f"🏫 Universitet reytingi: <b>#{rank_university or '—'}</b>\n"
        f"🇺🇿 Milliy reyting: <b>#{rank_national or '—'}</b>"
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _progress_bar(current: int, max_val: int, length: int = 8) -> str:
    """Visual ASCII progress bar: ████░░░░"""
    if max_val <= 0:
        return "░" * length
    filled = min(int(current / max_val * length), length)
    return "█" * filled + "░" * (length - filled)
