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
        # Graceful fallback if Ollama isn't running or no model
        summary = f"Xulosa yaratishda xatolik yuz berdi: {exc}"
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test yaratishda xatolik: {exc}",
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
