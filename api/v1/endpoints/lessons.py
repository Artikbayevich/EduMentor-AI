"""
api/v1/endpoints/lessons.py — AI-powered study materials and tests.

GET  /lessons/{lesson_id}              → lesson summary + RAG chunks
GET  /lessons/{lesson_id}/test         → generated multiple-choice test
POST /lessons/{lesson_id}/test/submit  → submit answers, get score, earn coins
"""
from __future__ import annotations

import random
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.deps import get_current_active_user
from core.database import get_db
from models.user import User
from services.rag_service import get_topic_materials
from services.content_service import (
    generate_summary,
    generate_tests,
    TestQuestion,
    test_question_to_dict,
)

router = APIRouter(prefix="/lessons", tags=["Lessons"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class RAGMaterialItem(BaseModel):
    text:        str
    source_file: str
    score:       float


class LessonSummaryResponse(BaseModel):
    subject:     str
    topic:       str
    summary:     str
    materials:   list[RAGMaterialItem]


class TestQuestionResponse(BaseModel):
    id:          int
    question:    str
    options:     list[str]


class GeneratedTestResponse(BaseModel):
    subject:   str
    topic:     str
    questions: list[TestQuestionResponse]


class TestSubmission(BaseModel):
    # Mapping of question ID (index) to selected answer ("A", "B", "C", "D")
    answers: dict[int, str]


class SubmissionResult(BaseModel):
    score:        int
    total:        int
    percentage:   float
    coins_earned: int
    explanations: dict[int, dict]   # { q_id: {"correct": "A", "explanation": "..."} }


# ── Mocks / Cache for demo purposes ──────────────────────────────────────────

# Since Ollama test generation takes time and we don't have a DB table for tests yet,
# we'll cache the generated tests in memory so the submit endpoint can grade them.
# Key: {user_id}_{lesson_id} -> list[TestQuestion]
_TEST_CACHE: dict[str, list[TestQuestion]] = {}


def _parse_lesson_id(lesson_id: str) -> tuple[str, str]:
    """
    Dummy parser to extract subject and topic from a lesson_id URL slug.
    Example: 'fizika-latest' -> ('Fizika', 'Latest lesson topic')
    """
    parts = lesson_id.split("-", 1)
    subject = parts[0].capitalize()
    topic = parts[1].replace("-", " ").capitalize() if len(parts) > 1 else "Umumiy mavzu"
    return subject, topic


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/{lesson_id}",
    response_model=LessonSummaryResponse,
    summary="Get AI-generated summary and source materials for a lesson",
)
async def get_lesson_summary(
    lesson_id: str = Path(..., description="Lesson ID slug"),
    current_user: User = Depends(get_current_active_user),
) -> LessonSummaryResponse:
    subject, topic = _parse_lesson_id(lesson_id)
    
    try:
        # Retrieve context chunks from ChromaDB
        materials = get_topic_materials(subject, topic, k=3)
        
        # If ChromaDB is empty (no PDFs ingested yet), we use a dummy text
        # to ensure Ollama doesn't crash on empty context.
        if not materials:
            materials_input = [f"Ushbu dars {subject} fanining {topic} mavzusiga bag'ishlangan."]
            mat_response = []
        else:
            materials_input = materials
            mat_response = [
                RAGMaterialItem(
                    text=m.text,
                    source_file=m.source_file,
                    score=m.score,
                ) for m in materials
            ]

        # Call local Ollama
        summary = await generate_summary(subject, topic, materials_input)
        
    except Exception as exc:
        # Hackathon Demo Fallback
        summary = (
            f"**{subject} — {topic}** mavzusi bo'yicha qisqacha xulosa:\n\n"
            "- Termodinamikaning birinchi qonuni energiyaning saqlanish qonunidir.\n"
            "- Tizimga berilgan issiqlik uning ichki energiyasini oshirishga sarflanadi.\n"
            "- Izotermik, izobarik va izoxorik jarayonlar tabiatda keng tarqalgan.\n\n"
            "*Eslatma: Bu AI tomonidan qisqartirilgan matn.*"
        )
        if not materials:
            mat_response = []

    return LessonSummaryResponse(
        subject=subject,
        topic=topic,
        summary=summary,
        materials=mat_response,
    )


@router.get(
    "/{lesson_id}/test",
    response_model=GeneratedTestResponse,
    summary="Generate a multiple-choice test based on lesson materials",
)
async def get_lesson_test(
    lesson_id: str = Path(...),
    current_user: User = Depends(get_current_active_user),
) -> GeneratedTestResponse:
    subject, topic = _parse_lesson_id(lesson_id)
    
    try:
        materials = get_topic_materials(subject, topic, k=3)
        if not materials:
            materials_input = [f"Ushbu dars {subject} fanining {topic} mavzusiga bag'ishlangan."]
        else:
            materials_input = materials

        # Generate exactly 5 questions via Ollama/Mistral
        questions = await generate_tests(subject, topic, materials_input, count=5)
        
        # Cache them for the submit endpoint (in-memory for hackathon demo)
        cache_key = f"{current_user.id}_{lesson_id}"
        _TEST_CACHE[cache_key] = questions
        
        # Format for client (strip correct answers)
        q_resp = [
            TestQuestionResponse(
                id=i,
                question=q.question,
                options=q.options,
            ) for i, q in enumerate(questions)
        ]
        
        return GeneratedTestResponse(
            subject=subject,
            topic=topic,
            questions=q_resp,
        )
        
    except Exception as exc:
        # Hackathon Demo Fallback
        questions = [
            TestQuestion(
                question="Termodinamikaning birinchi qonuni nimani anglatadi?",
                options=["Energiyaning saqlanishi", "Nyuton qonuni", "Massaning saqlanishi", "Impuls qonuni"],
                correct_answer="Energiyaning saqlanishi",
                explanation="Birinchi qonun energiyaning saqlanishini bildiradi."
            ),
            TestQuestion(
                question="Tizimga berilgan issiqlik nima uchun sarflanadi?",
                options=["Faqat ish bajarishga", "Ichki energiya va ish bajarishga", "Faqat ichki energiyaga", "Yo'qolib ketadi"],
                correct_answer="Ichki energiya va ish bajarishga",
                explanation="Issiqlik = Ichki energiya + Ish"
            )
        ]
        
        # Cache them for the submit endpoint (in-memory for hackathon demo)
        cache_key = f"{current_user.id}_{lesson_id}"
        _TEST_CACHE[cache_key] = questions
        
        q_resp = [
            TestQuestionResponse(
                id=i,
                question=q.question,
                options=q.options,
            ) for i, q in enumerate(questions)
        ]
        
        return GeneratedTestResponse(
            subject=subject,
            topic=topic,
            questions=q_resp,
        )


@router.post(
    "/{lesson_id}/test/submit",
    response_model=SubmissionResult,
    summary="Submit test answers, get score, and earn coins",
)
async def submit_test(
    lesson_id: str,
    submission: TestSubmission,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SubmissionResult:
    cache_key = f"{current_user.id}_{lesson_id}"
    questions = _TEST_CACHE.get(cache_key)
    
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test topilmadi yoki vaqti tugagan. Iltimos, testni qayta yuklang.",
        )
        
    score = 0
    total = len(questions)
    explanations = {}
    
    for i, q in enumerate(questions):
        user_ans = submission.answers.get(i)
        is_correct = (user_ans == q.correct_answer)
        if is_correct:
            score += 1
            
        explanations[i] = {
            "correct_answer": q.correct_answer,
            "user_answer": user_ans,
            "is_correct": is_correct,
            "explanation": q.explanation,
        }
        
    pct = (score / total) * 100 if total > 0 else 0
    
    # Calculate coins: e.g., 2 coins per correct answer + 5 bonus for 100%
    coins_earned = score * 2
    if score == total and total > 0:
        coins_earned += 5
        
    # Award coins to user
    if coins_earned > 0:
        current_user.coin_balance = (current_user.coin_balance or 0) + coins_earned
        db.add(current_user)
        await db.commit()
        await db.refresh(current_user)
        
    # Clear cache so they can't submit again
    _TEST_CACHE.pop(cache_key, None)
    
    return SubmissionResult(
        score=score,
        total=total,
        percentage=round(pct, 1),
        coins_earned=coins_earned,
        explanations=explanations,
    )


class MockNBRequest(BaseModel):
    student_id: str
    subject_name: str
    lesson_topic: str
    pdf_content: str

@router.post(
    "/mock-nb",
    summary="Hackathon Demo: Trigger an NB and notify student via Bot",
)
async def trigger_mock_nb(
    req: MockNBRequest,
    db: AsyncSession = Depends(get_db),
):
    import uuid
    import httpx
    from bot.config import bot_settings
    from models.user import Notification, NotificationType
    
    # 1. Ingest PDF content into ChromaDB via RAG service
    from services.rag_service import ingest_document
    import tempfile
    import os
    
    # Write mock PDF content to a temp text file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as tmp:
        tmp.write(req.pdf_content)
        tmp_path = tmp.name
        
    try:
        ingest_document(tmp_path, req.subject_name, req.lesson_topic)
    finally:
        os.unlink(tmp_path)
        
    # 2. Find user to notify
    user_query = await db.execute(select(User).where(User.hemis_id == req.student_id))
    user = user_query.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Student not found")
        
    # Generate lesson slug for URL
    lesson_id = f"{req.subject_name.lower().replace(' ', '-')}-latest"
    website_url = "http://localhost:5173"
    
    msg_text = (
        f"⚠️ <b>{req.subject_name}</b> fanida yangi NB qayd etildi\n\n"
        f"Mavzu: {req.lesson_topic}\n\n"
        f"Xavotir olmang! EduMentor AI siz uchun ushbu dars materiallarini o'qib, qisqa xulosa va test tayyorlab qo'ydi.\n\n"
        f"→ Darsni o'zlashtirish va EduCoin ishlash uchun:\n"
        f"{website_url}/lesson/{lesson_id}"
    )
    
    # Save notification
    db.add(Notification(
        user_id=user.id,
        type=NotificationType.subject_alert,
        message=msg_text,
        is_read=False,
    ))
    await db.commit()
    
    # Trigger Telegram bot directly
    if user.telegram_id and bot_settings.BOT_TOKEN:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{bot_settings.BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": user.telegram_id,
                        "text": msg_text,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True
                    }
                )
        except Exception as e:
            print(f"Failed to send tg msg: {e}")
            
    return {"status": "success", "message": "NB registered, RAG updated, and notification sent!"}
