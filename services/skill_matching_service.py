"""
skill_matching_service.py — Pure-Python AI skill matching for peer-to-peer learning.

Match logic (no ML required):
  • Intersection scoring  : can_teach ∩ want_learn weighted by skill level
  • Bidirectional bonus   : SWAP relationships score higher than one-way
  • University proximity  : +10 points for same university
  • Level compatibility   : teacher level ≥ learner level preferred

Public surface:
    calculate_match_score(user_a_skills, user_b_skills, *, same_university) → float
    determine_match_type(user_a_skills, user_b_skills)                       → MatchType
    find_matches(user_id, top_k, *, db)                                      → list[MatchResult]
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import NamedTuple

from loguru import logger


# ─── Enums & constants ────────────────────────────────────────────────────────

class MatchType(str, Enum):
    SWAP  = "SWAP"   # both users help each other
    MENTOR= "MENTOR" # only one side can help
    STUDY = "STUDY"  # same skills to learn together (study-buddy)


# Weights (must sum to 1.0 for clean 0-100 output)
_W_SKILL_MATCH   = 0.70   # core intersection score
_W_BIDIRECTIONAL = 0.20   # both directions active
_W_LEVEL_COMPAT  = 0.10   # teacher level ≥ learner level

_UNIVERSITY_BONUS = 10.0  # flat points added after weighted score
_MAX_SCORE        = 100.0


# ─── Lightweight data types (DB-agnostic) ─────────────────────────────────────

@dataclass(slots=True)
class SkillEntry:
    """Mirrors the `skills` table row — no SQLAlchemy dependency here."""
    skill_name: str
    skill_type: str          # "can_teach" | "want_learn"
    level:      int | None   # 1–5; None = unspecified


@dataclass(slots=True)
class UserSkillProfile:
    user_id:    uuid.UUID
    full_name:  str
    university: str
    can_teach:  list[SkillEntry] = field(default_factory=list)
    want_learn: list[SkillEntry] = field(default_factory=list)


@dataclass(slots=True)
class MatchResult:
    user_id:          uuid.UUID
    full_name:        str
    university:       str
    match_score:      float           # 0–100
    match_type:       MatchType
    can_help_with:    list[str]       # skills A can teach B
    needs_help_with:  list[str]       # skills B can teach A
    common_learning:  list[str]       # skills both want to learn


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _skill_index(skills: list[SkillEntry]) -> dict[str, int | None]:
    """
    Return {skill_name_lower: level} mapping.
    Duplicate names are resolved by taking the highest level.
    """
    index: dict[str, int | None] = {}
    for s in skills:
        key = s.skill_name.strip().lower()
        existing = index.get(key)
        if existing is None or (s.level is not None and (existing is None or s.level > existing)):
            index[key] = s.level
    return index


def _intersection_score(
    teachers: dict[str, int | None],
    learners:  dict[str, int | None],
) -> tuple[float, list[str]]:
    """
    Score how well *teachers* satisfies *learners*.

    Each matched skill contributes:
        base   = 1.0
        bonus  = +0.2 if teacher.level >= learner.level (competency fit)
        bonus  = +0.1 if teacher.level == 5 (expert)

    Returns (raw_score, matched_skill_names).
    """
    matched_names: list[str] = []
    raw_score = 0.0

    for skill, learner_level in learners.items():
        if skill not in teachers:
            continue
        matched_names.append(skill)
        teacher_level = teachers[skill]

        contribution = 1.0
        if teacher_level is not None and learner_level is not None:
            if teacher_level >= learner_level:
                contribution += 0.2
        if teacher_level == 5:
            contribution += 0.1

        raw_score += contribution

    return raw_score, matched_names


# ─── 1. Score calculation ─────────────────────────────────────────────────────

def calculate_match_score(
    user_a: UserSkillProfile,
    user_b: UserSkillProfile,
) -> float:
    """
    Compute a 0–100 compatibility score between two users.

    Formula (before university bonus):
        a_teaches_b  = intersection(a.can_teach, b.want_learn)  — weighted
        b_teaches_a  = intersection(b.can_teach, a.want_learn)  — weighted

        total_needed = |a.want_learn| + |b.want_learn|  (denominator cap)

        skill_score      = (a_teaches_b.raw + b_teaches_a.raw) / max(total_needed, 1)
        bidir_score      = 1.0 if both directions have ≥1 match else 0.0
        level_compat     = avg level-compatibility ratio across all matches

        weighted = (skill_score  * _W_SKILL_MATCH
                  + bidir_score  * _W_BIDIRECTIONAL
                  + level_compat * _W_LEVEL_COMPAT) * 100

        final = min(weighted + university_bonus, 100.0)

    Returns:
        float in [0.0, 100.0], rounded to 1 decimal place.
    """
    a_teach = _skill_index(user_a.can_teach)
    a_learn = _skill_index(user_a.want_learn)
    b_teach = _skill_index(user_b.can_teach)
    b_learn = _skill_index(user_b.want_learn)

    # Directional intersection scores
    a_to_b_score, _ = _intersection_score(a_teach, b_learn)
    b_to_a_score, _ = _intersection_score(b_teach, a_learn)

    total_needed = max(len(a_learn) + len(b_learn), 1)
    skill_score  = (a_to_b_score + b_to_a_score) / total_needed

    # Bidirectional bonus (0 or 1)
    bidir_score = 1.0 if (a_to_b_score > 0 and b_to_a_score > 0) else 0.0

    # Level compatibility: ratio of matches where teacher.level >= learner.level
    compat_hits = total_compat = 0
    for teach_idx, learn_idx in [(a_teach, b_learn), (b_teach, a_learn)]:
        for skill, l_lvl in learn_idx.items():
            if skill in teach_idx:
                total_compat += 1
                t_lvl = teach_idx[skill]
                if t_lvl is None or l_lvl is None or t_lvl >= l_lvl:
                    compat_hits += 1

    level_compat = (compat_hits / total_compat) if total_compat else 0.0

    # Weighted sum → 0-100
    weighted = (
        skill_score  * _W_SKILL_MATCH
        + bidir_score  * _W_BIDIRECTIONAL
        + level_compat * _W_LEVEL_COMPAT
    ) * 100.0

    # University proximity bonus
    same_uni = user_a.university.strip().lower() == user_b.university.strip().lower()
    if same_uni and weighted > 0:
        weighted += _UNIVERSITY_BONUS

    return round(min(weighted, _MAX_SCORE), 1)


# ─── 2. Match type classifier ─────────────────────────────────────────────────

def determine_match_type(
    user_a: UserSkillProfile,
    user_b: UserSkillProfile,
) -> MatchType:
    """
    Classify the relationship between two users:

    SWAP   — A teaches B something AND B teaches A something
    MENTOR — Only one direction has matched skills (unidirectional help)
    STUDY  — No teaching overlap but they share ≥1 common skill to learn

    Returns MatchType enum value.
    """
    a_teach = _skill_index(user_a.can_teach)
    a_learn = _skill_index(user_a.want_learn)
    b_teach = _skill_index(user_b.can_teach)
    b_learn = _skill_index(user_b.want_learn)

    a_helps_b = any(s in a_teach for s in b_learn)
    b_helps_a = any(s in b_teach for s in a_learn)

    if a_helps_b and b_helps_a:
        return MatchType.SWAP

    if a_helps_b or b_helps_a:
        return MatchType.MENTOR

    # Check common learning interests (study-buddy)
    common = set(a_learn.keys()) & set(b_learn.keys())
    if common:
        return MatchType.STUDY

    return MatchType.STUDY   # fallback — still worth connecting


# ─── 3. find_matches ─────────────────────────────────────────────────────────

def find_matches(
    target: UserSkillProfile,
    candidates: list[UserSkillProfile],
    top_k: int = 10,
    min_score: float = 5.0,
) -> list[MatchResult]:
    """
    Rank all candidate users by their match score with *target*.

    Args:
        target     : The user we are finding matches for.
        candidates : All other users with their skill profiles.
                     (Exclude target from this list before calling.)
        top_k      : Maximum number of results to return.
        min_score  : Drop results below this threshold (noise filter).

    Returns:
        List of MatchResult sorted by match_score descending.
    """
    logger.debug(
        "find_matches: user={} candidates={} top_k={}",
        target.user_id, len(candidates), top_k,
    )

    results: list[MatchResult] = []

    target_teach = _skill_index(target.can_teach)
    target_learn = _skill_index(target.want_learn)

    for candidate in candidates:
        if candidate.user_id == target.user_id:
            continue

        score = calculate_match_score(target, candidate)
        if score < min_score:
            continue

        match_type = determine_match_type(target, candidate)

        # Skills target can help candidate with
        cand_learn = _skill_index(candidate.want_learn)
        _, can_help = _intersection_score(target_teach, cand_learn)

        # Skills candidate can help target with
        cand_teach = _skill_index(candidate.can_teach)
        _, needs_help = _intersection_score(cand_teach, target_learn)

        # Common learning interests (study-buddy dimension)
        common_learning = sorted(
            set(target_learn.keys()) & set(cand_learn.keys())
        )

        results.append(
            MatchResult(
                user_id=candidate.user_id,
                full_name=candidate.full_name,
                university=candidate.university,
                match_score=score,
                match_type=match_type,
                can_help_with=sorted(can_help),
                needs_help_with=sorted(needs_help),
                common_learning=common_learning,
            )
        )

    results.sort(key=lambda r: r.match_score, reverse=True)
    top = results[:top_k]

    logger.info(
        "find_matches: {} results for user={} (top score: {})",
        len(top),
        target.user_id,
        top[0].match_score if top else "N/A",
    )
    return top


# ─── DB integration layer (async, SQLAlchemy) ────────────────────────────────

async def load_user_profile(
    user_id: uuid.UUID,
    db,                     # AsyncSession — typed loosely to avoid circular imports
) -> UserSkillProfile | None:
    """
    Load a UserSkillProfile from the database for a given user_id.

    Returns None if the user does not exist.
    """
    from sqlalchemy import select
    from models.user import User, Skill

    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user: User | None = result.scalar_one_or_none()
    if user is None:
        return None

    skills_result = await db.execute(
        select(Skill).where(Skill.user_id == user_id)
    )
    skill_rows = skills_result.scalars().all()

    can_teach  = [
        SkillEntry(skill_name=s.skill_name, skill_type="can_teach",  level=s.level)
        for s in skill_rows if s.type == "can_teach"
    ]
    want_learn = [
        SkillEntry(skill_name=s.skill_name, skill_type="want_learn", level=s.level)
        for s in skill_rows if s.type == "want_learn"
    ]

    return UserSkillProfile(
        user_id=user.id,
        full_name=user.full_name,
        university=user.university,
        can_teach=can_teach,
        want_learn=want_learn,
    )


async def load_all_profiles(
    db,
    exclude_user_id: uuid.UUID | None = None,
) -> list[UserSkillProfile]:
    """Load all active user skill profiles, optionally excluding one user."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from models.user import User, Skill

    query = select(User).where(User.is_active.is_(True))
    if exclude_user_id:
        query = query.where(User.id != exclude_user_id)

    result  = await db.execute(query)
    users   = result.scalars().all()

    # Batch-load all skills in one query
    user_ids = [u.id for u in users]
    if not user_ids:
        return []

    skills_result = await db.execute(
        select(Skill).where(Skill.user_id.in_(user_ids))
    )
    all_skills = skills_result.scalars().all()

    # Group by user_id
    from collections import defaultdict
    skills_by_user: dict[uuid.UUID, list[Skill]] = defaultdict(list)
    for s in all_skills:
        skills_by_user[s.user_id].append(s)

    profiles: list[UserSkillProfile] = []
    for user in users:
        rows = skills_by_user.get(user.id, [])
        profiles.append(
            UserSkillProfile(
                user_id=user.id,
                full_name=user.full_name,
                university=user.university,
                can_teach=[
                    SkillEntry(skill_name=s.skill_name, skill_type="can_teach",  level=s.level)
                    for s in rows if s.type == "can_teach"
                ],
                want_learn=[
                    SkillEntry(skill_name=s.skill_name, skill_type="want_learn", level=s.level)
                    for s in rows if s.type == "want_learn"
                ],
            )
        )
    return profiles


async def find_matches_for_user(
    user_id: uuid.UUID,
    db,
    top_k: int = 10,
    min_score: float = 5.0,
) -> list[MatchResult]:
    """
    Full async pipeline: load target + all candidates from DB, run matching.

    This is the main entry point for the API layer.
    """
    target = await load_user_profile(user_id, db)
    if target is None:
        logger.warning("find_matches_for_user: user {} not found", user_id)
        return []

    candidates = await load_all_profiles(db, exclude_user_id=user_id)

    if not candidates:
        logger.info("find_matches_for_user: no other users in DB yet")
        return []

    return find_matches(target, candidates, top_k=top_k, min_score=min_score)


# ─── Serialisation helpers ────────────────────────────────────────────────────

def match_result_to_dict(r: MatchResult) -> dict:
    return {
        "user_id":         str(r.user_id),
        "full_name":       r.full_name,
        "university":      r.university,
        "match_score":     r.match_score,
        "match_type":      r.match_type.value,
        "can_help_with":   r.can_help_with,
        "needs_help_with": r.needs_help_with,
        "common_learning": r.common_learning,
    }


def user_profile_to_dict(p: UserSkillProfile) -> dict:
    return {
        "user_id":    str(p.user_id),
        "full_name":  p.full_name,
        "university": p.university,
        "can_teach":  [{"skill": s.skill_name, "level": s.level} for s in p.can_teach],
        "want_learn": [{"skill": s.skill_name, "level": s.level} for s in p.want_learn],
    }
