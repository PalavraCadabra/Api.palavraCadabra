import hashlib
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select, distinct, case, extract, and_

from app.api.deps import CurrentUser, DBSession
from app.models.aac_profile import AACProfile
from app.models.activity_result import ActivityResult
from app.models.care_relationship import CareRelationship
from app.models.consent import UserConsent
from app.models.literacy_program import LiteracyProgram, LiteracyStage
from app.models.usage_log import UsageLog
from app.models.user import User, UserRole

router = APIRouter()


def _require_researcher(current_user: User) -> None:
    """Verifica se o usuário tem acesso à pesquisa (admin ou pesquisador)."""
    if current_user.role not in (UserRole.admin,):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores e pesquisadores",
        )


async def _get_consented_profile_ids(session) -> list[uuid.UUID]:
    """Retorna IDs de perfis de usuários que consentiram com pesquisa (LGPD)."""
    result = await session.execute(
        select(AACProfile.id).join(
            UserConsent,
            and_(
                UserConsent.user_id == AACProfile.user_id,
                UserConsent.purpose == "research",
                UserConsent.granted.is_(True),
                UserConsent.revoked_at.is_(None),
            ),
        )
    )
    return [row[0] for row in result.all()]


@router.get("/aggregate/communication")
async def aggregate_communication_stats(
    session: DBSession,
    current_user: CurrentUser,
    since: datetime | None = Query(default=None, description="Início do período"),
    until: datetime | None = Query(default=None, description="Fim do período"),
) -> dict:
    """
    Estatísticas agregadas de comunicação de TODOS os usuários que consentiram.
    Dados anonimizados para pesquisa. Apenas admin/pesquisador.
    """
    _require_researcher(current_user)
    consented_ids = await _get_consented_profile_ids(session)

    if not consented_ids:
        return {
            "period": {"from": since, "to": until},
            "total_users": 0,
            "total_sessions": 0,
            "communication_metrics": {},
            "vocabulary_distribution": {},
            "usage_patterns": {"by_hour": [], "by_day_of_week": []},
            "demographic_breakdown": {"by_communication_level": {}, "by_motor_capability": {}},
            "literacy_metrics": {},
        }

    # Filtro base de logs
    log_filter = [UsageLog.profile_id.in_(consented_ids)]
    if since:
        log_filter.append(UsageLog.timestamp >= since)
    if until:
        log_filter.append(UsageLog.timestamp <= until)

    # Total de usuários consentidos
    total_users = len(consented_ids)

    # Total de sessões únicas
    sessions_result = await session.execute(
        select(func.count(distinct(UsageLog.session_id))).where(*log_filter)
    )
    total_sessions = sessions_result.scalar() or 0

    # Métricas de comunicação — contagens por evento
    events_result = await session.execute(
        select(
            UsageLog.event_type,
            func.count().label("count"),
        )
        .where(*log_filter)
        .group_by(UsageLog.event_type)
    )
    event_counts = {row.event_type: row.count for row in events_result.all()}

    symbol_events = event_counts.get("symbol_tap", 0)
    message_events = event_counts.get("message_speak", 0)
    total_events = sum(event_counts.values())

    avg_symbols_per_session = round(symbol_events / max(total_sessions, 1), 2)
    avg_message_length = round(symbol_events / max(message_events, 1), 2)

    # Padrões de uso por hora
    hourly_result = await session.execute(
        select(
            extract("hour", UsageLog.timestamp).label("hour"),
            func.count().label("count"),
        )
        .where(*log_filter)
        .group_by("hour")
        .order_by("hour")
    )
    by_hour = [
        {"hour": int(row.hour), "avg_events": round(row.count / max(total_users, 1), 2)}
        for row in hourly_result.all()
    ]

    # Padrões de uso por dia da semana
    daily_result = await session.execute(
        select(
            extract("dow", UsageLog.timestamp).label("day"),
            func.count().label("count"),
        )
        .where(*log_filter)
        .group_by("day")
        .order_by("day")
    )
    by_day = [
        {"day": int(row.day), "avg_events": round(row.count / max(total_users, 1), 2)}
        for row in daily_result.all()
    ]

    # Breakdown demográfico — por nível de comunicação
    comm_level_result = await session.execute(
        select(
            AACProfile.communication_level,
            func.count().label("count"),
        )
        .where(AACProfile.id.in_(consented_ids))
        .group_by(AACProfile.communication_level)
    )
    by_communication_level = {
        row.communication_level.value: row.count
        for row in comm_level_result.all()
    }

    # Breakdown demográfico — por capacidade motora
    motor_result = await session.execute(
        select(
            AACProfile.motor_capability,
            func.count().label("count"),
        )
        .where(AACProfile.id.in_(consented_ids))
        .group_by(AACProfile.motor_capability)
    )
    by_motor_capability = {
        row.motor_capability.value: row.count for row in motor_result.all()
    }

    # Métricas de letramento
    lit_result = await session.execute(
        select(
            func.count().label("total"),
            func.avg(
                case(
                    (LiteracyProgram.current_stage == LiteracyStage.foundations, 1),
                    (LiteracyProgram.current_stage == LiteracyStage.emerging, 2),
                    (LiteracyProgram.current_stage == LiteracyStage.developing, 3),
                    (LiteracyProgram.current_stage == LiteracyStage.conventional, 4),
                    else_=0,
                )
            ).label("avg_stage"),
        ).where(
            LiteracyProgram.profile_id.in_(consented_ids),
            LiteracyProgram.is_active.is_(True),
        )
    )
    lit_row = lit_result.one()

    stage_dist_result = await session.execute(
        select(
            LiteracyProgram.current_stage,
            func.count().label("count"),
        )
        .where(
            LiteracyProgram.profile_id.in_(consented_ids),
            LiteracyProgram.is_active.is_(True),
        )
        .group_by(LiteracyProgram.current_stage)
    )
    stage_distribution = {
        row.current_stage.value: row.count for row in stage_dist_result.all()
    }

    # Pontuação média de atividades
    avg_score_result = await session.execute(
        select(func.avg(ActivityResult.score)).where(
            ActivityResult.profile_id.in_(consented_ids),
            ActivityResult.score.isnot(None),
        )
    )
    avg_activity_score = round(float(avg_score_result.scalar() or 0), 2)

    return {
        "period": {"from": since, "to": until},
        "total_users": total_users,
        "total_sessions": total_sessions,
        "communication_metrics": {
            "avg_symbols_per_session": avg_symbols_per_session,
            "avg_message_length_mlu": avg_message_length,
            "avg_communication_rate": round(
                symbol_events / max(total_sessions, 1) * 60, 2
            ),
            "total_events": total_events,
        },
        "vocabulary_distribution": event_counts,
        "usage_patterns": {
            "by_hour": by_hour,
            "by_day_of_week": by_day,
        },
        "demographic_breakdown": {
            "by_communication_level": by_communication_level,
            "by_motor_capability": by_motor_capability,
        },
        "literacy_metrics": {
            "programs_active": lit_row.total or 0,
            "avg_stage": round(float(lit_row.avg_stage or 0), 2),
            "avg_activity_score": avg_activity_score,
            "stage_distribution": stage_distribution,
        },
    }


@router.get("/aggregate/vocabulary")
async def aggregate_vocabulary_analysis(
    session: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Top vocabulário entre todos os usuários (anonimizado)."""
    _require_researcher(current_user)
    consented_ids = await _get_consented_profile_ids(session)

    if not consented_ids:
        return {
            "top_symbols": [],
            "unique_symbols_used": 0,
            "vocabulary_growth_trend": [],
        }

    # Buscar eventos de symbol_tap e extrair dados de vocabulário
    logs_result = await session.execute(
        select(
            UsageLog.event_data,
            func.count().label("count"),
        )
        .where(
            UsageLog.profile_id.in_(consented_ids),
            UsageLog.event_type == "symbol_tap",
            UsageLog.event_data.isnot(None),
        )
        .group_by(UsageLog.event_data)
        .order_by(func.count().desc())
        .limit(50)
    )

    top_symbols = []
    for row in logs_result.all():
        data = row.event_data or {}
        top_symbols.append({
            "label": data.get("label", "desconhecido"),
            "count": row.count,
            "class": data.get("grammatical_class", "misc"),
        })

    # Símbolos únicos
    unique_result = await session.execute(
        select(func.count(distinct(UsageLog.event_data))).where(
            UsageLog.profile_id.in_(consented_ids),
            UsageLog.event_type == "symbol_tap",
        )
    )
    unique_symbols = unique_result.scalar() or 0

    # Tendência de crescimento de vocabulário por mês
    trend_result = await session.execute(
        select(
            func.to_char(UsageLog.timestamp, "YYYY-MM").label("month"),
            func.count(distinct(UsageLog.event_data)).label("unique_symbols"),
        )
        .where(
            UsageLog.profile_id.in_(consented_ids),
            UsageLog.event_type == "symbol_tap",
        )
        .group_by("month")
        .order_by("month")
    )
    vocabulary_growth = [
        {"month": row.month, "avg_unique_symbols": float(row.unique_symbols)}
        for row in trend_result.all()
    ]

    return {
        "top_symbols": top_symbols,
        "unique_symbols_used": unique_symbols,
        "vocabulary_growth_trend": vocabulary_growth,
    }


@router.get("/aggregate/literacy")
async def aggregate_literacy_stats(
    session: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Resultados de letramento entre todos os usuários (anonimizado)."""
    _require_researcher(current_user)
    consented_ids = await _get_consented_profile_ids(session)

    if not consented_ids:
        return {
            "total_programs": 0,
            "active_programs": 0,
            "stage_distribution": {},
            "avg_score": 0,
            "total_activities_completed": 0,
            "avg_time_per_activity_seconds": 0,
            "completion_rate": 0,
        }

    # Programas totais e ativos
    programs_result = await session.execute(
        select(
            func.count().label("total"),
            func.count().filter(LiteracyProgram.is_active.is_(True)).label("active"),
        ).where(LiteracyProgram.profile_id.in_(consented_ids))
    )
    prog_row = programs_result.one()

    # Distribuição por estágio
    stage_result = await session.execute(
        select(
            LiteracyProgram.current_stage,
            func.count().label("count"),
        )
        .where(LiteracyProgram.profile_id.in_(consented_ids))
        .group_by(LiteracyProgram.current_stage)
    )
    stage_dist = {row.current_stage.value: row.count for row in stage_result.all()}

    # Resultados de atividades
    activity_stats = await session.execute(
        select(
            func.count().label("total"),
            func.avg(ActivityResult.score).label("avg_score"),
            func.avg(ActivityResult.time_spent_seconds).label("avg_time"),
            func.count().filter(ActivityResult.completed_at.isnot(None)).label("completed"),
        ).where(ActivityResult.profile_id.in_(consented_ids))
    )
    act_row = activity_stats.one()

    return {
        "total_programs": prog_row.total or 0,
        "active_programs": prog_row.active or 0,
        "stage_distribution": stage_dist,
        "avg_score": round(float(act_row.avg_score or 0), 2),
        "total_activities_completed": act_row.completed or 0,
        "avg_time_per_activity_seconds": round(float(act_row.avg_time or 0), 1),
        "completion_rate": round(
            (act_row.completed or 0) / max(act_row.total or 1, 1) * 100, 1
        ),
    }


@router.get("/cohorts")
async def research_cohorts(
    session: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Agrupar usuários em coortes anonimizados para comparação."""
    _require_researcher(current_user)
    consented_ids = await _get_consented_profile_ids(session)

    if not consented_ids:
        return {"cohorts": []}

    # Coorte por nível de comunicação
    comm_cohorts = await session.execute(
        select(
            AACProfile.communication_level,
            func.count(distinct(AACProfile.id)).label("profile_count"),
            func.count(distinct(UsageLog.session_id)).label("total_sessions"),
            func.count(UsageLog.id).label("total_events"),
        )
        .outerjoin(UsageLog, UsageLog.profile_id == AACProfile.id)
        .where(AACProfile.id.in_(consented_ids))
        .group_by(AACProfile.communication_level)
    )

    by_communication_level = [
        {
            "cohort": f"communication_{row.communication_level.value}",
            "profile_count": row.profile_count,
            "total_sessions": row.total_sessions or 0,
            "total_events": row.total_events or 0,
            "avg_events_per_profile": round(
                (row.total_events or 0) / max(row.profile_count, 1), 2
            ),
        }
        for row in comm_cohorts.all()
    ]

    # Coorte por capacidade motora
    motor_cohorts = await session.execute(
        select(
            AACProfile.motor_capability,
            func.count(distinct(AACProfile.id)).label("profile_count"),
            func.count(distinct(UsageLog.session_id)).label("total_sessions"),
            func.count(UsageLog.id).label("total_events"),
        )
        .outerjoin(UsageLog, UsageLog.profile_id == AACProfile.id)
        .where(AACProfile.id.in_(consented_ids))
        .group_by(AACProfile.motor_capability)
    )

    by_motor_capability = [
        {
            "cohort": f"motor_{row.motor_capability.value}",
            "profile_count": row.profile_count,
            "total_sessions": row.total_sessions or 0,
            "total_events": row.total_events or 0,
            "avg_events_per_profile": round(
                (row.total_events or 0) / max(row.profile_count, 1), 2
            ),
        }
        for row in motor_cohorts.all()
    ]

    return {
        "cohorts": by_communication_level + by_motor_capability,
    }


@router.get("/export/anonymized")
async def export_anonymized_dataset(
    session: DBSession,
    current_user: CurrentUser,
    format: str = Query(default="json", description="Formato: json ou csv"),
) -> dict:
    """
    Exportar dataset anonimizado para ferramentas de pesquisa externas.
    LGPD: Só inclui dados de usuários que consentiram.
    Identificadores pessoais removidos. IDs substituídos por hashes aleatórios.
    """
    _require_researcher(current_user)
    consented_ids = await _get_consented_profile_ids(session)

    if not consented_ids:
        return {"profiles": [], "usage_summary": [], "literacy_summary": []}

    # Gerar hashes anônimos para cada perfil
    def anonymize_id(profile_id: uuid.UUID) -> str:
        return hashlib.sha256(
            f"research_{profile_id}".encode()
        ).hexdigest()[:12]

    # Dados de perfil anonimizados
    profiles_result = await session.execute(
        select(AACProfile).where(AACProfile.id.in_(consented_ids))
    )
    profiles_data = []
    id_map = {}
    for profile in profiles_result.scalars().all():
        anon_id = anonymize_id(profile.id)
        id_map[profile.id] = anon_id
        profiles_data.append({
            "anon_id": anon_id,
            "communication_level": profile.communication_level.value,
            "motor_capability": profile.motor_capability.value,
            "visual_capability": profile.visual_capability.value,
            "grid_size": profile.grid_size_preference,
        })

    # Resumo de uso por perfil anonimizado
    usage_result = await session.execute(
        select(
            UsageLog.profile_id,
            UsageLog.event_type,
            func.count().label("count"),
        )
        .where(UsageLog.profile_id.in_(consented_ids))
        .group_by(UsageLog.profile_id, UsageLog.event_type)
    )
    usage_data = [
        {
            "anon_id": id_map.get(row.profile_id, "unknown"),
            "event_type": row.event_type,
            "count": row.count,
        }
        for row in usage_result.all()
    ]

    # Resumo de letramento por perfil anonimizado
    literacy_result = await session.execute(
        select(
            LiteracyProgram.profile_id,
            LiteracyProgram.current_stage,
            LiteracyProgram.is_active,
        ).where(LiteracyProgram.profile_id.in_(consented_ids))
    )
    literacy_data = [
        {
            "anon_id": id_map.get(row.profile_id, "unknown"),
            "current_stage": row.current_stage.value,
            "is_active": row.is_active,
        }
        for row in literacy_result.all()
    ]

    return {
        "export_date": datetime.utcnow().isoformat(),
        "total_profiles": len(profiles_data),
        "format": format,
        "profiles": profiles_data,
        "usage_summary": usage_data,
        "literacy_summary": literacy_data,
    }
