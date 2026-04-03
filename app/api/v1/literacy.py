import uuid
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DBSession
from app.models.aac_profile import AACProfile
from app.models.activity_result import ActivityResult
from app.models.literacy_activity import ActivityType, LiteracyActivity
from app.models.literacy_milestone import LiteracyMilestone
from app.models.literacy_program import LiteracyProgram, LiteracyStage
from app.schemas.literacy import (
    ActivityResultCreate,
    ActivityResultRead,
    LiteracyActivityCreate,
    LiteracyActivityRead,
    LiteracyProgramCreate,
    LiteracyProgramRead,
    LiteracyProgramUpdate,
    LiteracyProgressSummary,
)

router = APIRouter()

# ──────────────────────────── Programs ────────────────────────────


@router.post("/programs", response_model=LiteracyProgramRead, status_code=status.HTTP_201_CREATED)
async def create_program(
    data: LiteracyProgramCreate,
    session: DBSession,
    current_user: CurrentUser,
) -> LiteracyProgram:
    program = LiteracyProgram(
        profile_id=data.profile_id,
        assigned_by=current_user.id,
        name=data.name,
        current_stage=LiteracyStage(data.current_stage),
        notes=data.notes,
    )
    session.add(program)
    await session.flush()
    await session.refresh(program)
    return program


@router.get("/programs", response_model=list[LiteracyProgramRead])
async def list_programs(
    session: DBSession,
    current_user: CurrentUser,
    profile_id: uuid.UUID | None = Query(default=None),
) -> list[LiteracyProgram]:
    stmt = select(LiteracyProgram).where(LiteracyProgram.assigned_by == current_user.id)
    if profile_id:
        stmt = stmt.where(LiteracyProgram.profile_id == profile_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/programs/{program_id}", response_model=LiteracyProgramRead)
async def get_program(
    program_id: uuid.UUID,
    session: DBSession,
    current_user: CurrentUser,
) -> LiteracyProgram:
    result = await session.execute(
        select(LiteracyProgram).where(
            LiteracyProgram.id == program_id,
            LiteracyProgram.assigned_by == current_user.id,
        )
    )
    program = result.scalar_one_or_none()
    if not program:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
    return program


@router.patch("/programs/{program_id}", response_model=LiteracyProgramRead)
async def update_program(
    program_id: uuid.UUID,
    data: LiteracyProgramUpdate,
    session: DBSession,
    current_user: CurrentUser,
) -> LiteracyProgram:
    result = await session.execute(
        select(LiteracyProgram).where(
            LiteracyProgram.id == program_id,
            LiteracyProgram.assigned_by == current_user.id,
        )
    )
    program = result.scalar_one_or_none()
    if not program:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")

    update_data = data.model_dump(exclude_unset=True)
    if "current_stage" in update_data and update_data["current_stage"] is not None:
        update_data["current_stage"] = LiteracyStage(update_data["current_stage"])
    for field, value in update_data.items():
        setattr(program, field, value)
    await session.flush()
    await session.refresh(program)
    return program


# ──────────────────────────── Activities ────────────────────────────


@router.get("/activities", response_model=list[LiteracyActivityRead])
async def list_activities(
    session: DBSession,
    current_user: CurrentUser,
    stage: str | None = Query(default=None),
    activity_type: str | None = Query(default=None),
) -> list[LiteracyActivity]:
    stmt = select(LiteracyActivity)
    if stage:
        stmt = stmt.where(LiteracyActivity.stage == LiteracyStage(stage))
    if activity_type:
        stmt = stmt.where(LiteracyActivity.activity_type == ActivityType(activity_type))
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.post("/activities", response_model=LiteracyActivityRead, status_code=status.HTTP_201_CREATED)
async def create_activity(
    data: LiteracyActivityCreate,
    session: DBSession,
    current_user: CurrentUser,
) -> LiteracyActivity:
    activity = LiteracyActivity(
        activity_type=ActivityType(data.activity_type),
        stage=LiteracyStage(data.stage),
        title=data.title,
        description=data.description,
        difficulty_level=data.difficulty_level,
        content=data.content,
        symbol_ids=data.symbol_ids,
        estimated_duration_minutes=data.estimated_duration_minutes,
        is_template=True,
        created_by=current_user.id,
    )
    session.add(activity)
    await session.flush()
    await session.refresh(activity)
    return activity


@router.get("/activities/{activity_id}", response_model=LiteracyActivityRead)
async def get_activity(
    activity_id: uuid.UUID,
    session: DBSession,
    current_user: CurrentUser,
) -> LiteracyActivity:
    result = await session.execute(
        select(LiteracyActivity).where(LiteracyActivity.id == activity_id)
    )
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")
    return activity


# ──────────────────────────── Results ────────────────────────────


@router.post("/results", response_model=ActivityResultRead, status_code=status.HTTP_201_CREATED)
async def submit_result(
    data: ActivityResultCreate,
    session: DBSession,
    current_user: CurrentUser,
) -> ActivityResult:
    result = ActivityResult(
        program_id=data.program_id,
        activity_id=data.activity_id,
        profile_id=data.profile_id,
        score=data.score,
        correct_answers=data.correct_answers,
        total_questions=data.total_questions,
        time_spent_seconds=data.time_spent_seconds,
        responses=data.responses,
        notes=data.notes,
        recorded_by=current_user.id,
        completed_at=datetime.now(timezone.utc) if data.score is not None else None,
    )
    session.add(result)
    await session.flush()
    await session.refresh(result)
    return result


@router.get("/results", response_model=list[ActivityResultRead])
async def list_results(
    session: DBSession,
    current_user: CurrentUser,
    program_id: uuid.UUID | None = Query(default=None),
    profile_id: uuid.UUID | None = Query(default=None),
) -> list[ActivityResult]:
    stmt = select(ActivityResult)
    if program_id:
        stmt = stmt.where(ActivityResult.program_id == program_id)
    if profile_id:
        stmt = stmt.where(ActivityResult.profile_id == profile_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


# ──────────────────────────── Progress ────────────────────────────


STAGE_RECOMMENDATIONS: dict[str, list[str]] = {
    "foundations": [
        "Continue praticando pareamento de simbolos com palavras faladas.",
        "Explore atividades de consciencia fonologica com rimas.",
        "Reforce o reconhecimento de letras diariamente.",
    ],
    "emerging": [
        "Trabalhe correspondencia letra-som com as vogais.",
        "Introduza palavras de alta frequencia no dia a dia.",
        "Use leitura compartilhada com suporte de simbolos CAA.",
    ],
    "developing": [
        "Pratique decodificacao de silabas simples (CA, DA, MA).",
        "Monte frases curtas usando palavras conhecidas.",
        "Faca a ponte entre simbolos e texto escrito.",
    ],
    "conventional": [
        "Incentive leitura independente de textos curtos adaptados.",
        "Pratique escrita funcional de mensagens simples.",
        "Use comunicacao por texto no dia a dia.",
    ],
}


@router.get("/progress/{program_id}", response_model=LiteracyProgressSummary)
async def get_progress(
    program_id: uuid.UUID,
    session: DBSession,
    current_user: CurrentUser,
) -> LiteracyProgressSummary:
    # Fetch program
    prog_result = await session.execute(
        select(LiteracyProgram).where(
            LiteracyProgram.id == program_id,
            LiteracyProgram.assigned_by == current_user.id,
        )
    )
    program = prog_result.scalar_one_or_none()
    if not program:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")

    # Fetch profile name
    profile_result = await session.execute(
        select(AACProfile.name).where(AACProfile.id == program.profile_id)
    )
    profile_name = profile_result.scalar_one_or_none() or "Unknown"

    # Fetch all results for this program
    results_stmt = (
        select(ActivityResult)
        .where(ActivityResult.program_id == program_id)
        .where(ActivityResult.completed_at.is_not(None))
    )
    results = (await session.execute(results_stmt)).scalars().all()

    # Compute aggregates
    total_completed = len(results)
    total_score = sum(r.score for r in results if r.score is not None)
    scored_count = sum(1 for r in results if r.score is not None)
    average_score = round(total_score / scored_count, 1) if scored_count else 0.0
    total_time = sum(r.time_spent_seconds for r in results)

    # Group by activity type
    by_type: dict[str, dict] = defaultdict(lambda: {"completed": 0, "total_score": 0, "scored": 0})
    for r in results:
        # Eagerly loaded activity
        atype = r.activity.activity_type.value if r.activity else "unknown"
        by_type[atype]["completed"] += 1
        if r.score is not None:
            by_type[atype]["total_score"] += r.score
            by_type[atype]["scored"] += 1

    activities_by_type = {}
    for atype, data in by_type.items():
        avg = round(data["total_score"] / data["scored"], 1) if data["scored"] else 0.0
        activities_by_type[atype] = {"completed": data["completed"], "avg_score": avg}

    # Fetch milestones
    milestones_result = await session.execute(
        select(LiteracyMilestone).where(LiteracyMilestone.profile_id == program.profile_id)
    )
    milestones = [
        {
            "type": m.milestone_type,
            "stage": m.stage.value,
            "achieved_at": m.achieved_at.isoformat(),
        }
        for m in milestones_result.scalars().all()
    ]

    # Recommendations based on current stage
    recommendations = STAGE_RECOMMENDATIONS.get(program.current_stage.value, [])

    return LiteracyProgressSummary(
        program_id=program.id,
        profile_name=profile_name,
        current_stage=program.current_stage.value,
        total_activities_completed=total_completed,
        average_score=average_score,
        total_time_minutes=total_time // 60,
        activities_by_type=activities_by_type,
        milestones=milestones,
        recommendations=recommendations,
    )
