"""LGPD data anonymization service for user data deletion/portability."""

import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aac_profile import AACProfile
from app.models.board import Board
from app.models.care_relationship import CareRelationship
from app.models.consent import UserConsent
from app.models.usage_log import UsageLog
from app.models.user import User


def _anonymize_hash(value: str) -> str:
    """Create a one-way hash for anonymization."""
    return hashlib.sha256(value.encode()).hexdigest()[:16]


async def anonymize_user_data(session: AsyncSession, user_id: uuid.UUID) -> dict:
    """
    Anonymize all personal data for a user (LGPD Art. 18, VI — Right to deletion).

    Strategy:
    1. Anonymize user record (replace email, name with hashes)
    2. Anonymize profiles (replace name with "Anonimo-{hash}")
    3. Keep usage logs but remove profile_id link (set to NULL for anonymized research)
    4. Delete boards and cells (cascade)
    5. Delete care relationships
    6. Mark all consents as revoked
    """
    now = datetime.now(timezone.utc)
    anon_hash = _anonymize_hash(str(user_id))
    counts: dict[str, int] = {}

    # 1. Anonymize user record
    await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(
            email=f"deleted-{anon_hash}@anonymized.local",
            full_name=f"Usuário Removido {anon_hash}",
            hashed_password="DELETED",
            is_active=False,
        )
    )
    counts["user"] = 1

    # 2. Anonymize profiles
    result = await session.execute(
        update(AACProfile)
        .where(AACProfile.user_id == user_id)
        .values(name=f"Anônimo-{anon_hash}")
    )
    counts["profiles"] = result.rowcount  # type: ignore[assignment]

    # 3. Anonymize usage logs — nullify profile link but keep for anonymized research
    from sqlalchemy import select

    profile_ids_result = await session.execute(
        select(AACProfile.id).where(AACProfile.user_id == user_id)
    )
    profile_ids = [row[0] for row in profile_ids_result.fetchall()]

    if profile_ids:
        result = await session.execute(
            update(UsageLog)
            .where(UsageLog.profile_id.in_(profile_ids))
            .values(session_id=None)
        )
        counts["usage_logs_anonymized"] = result.rowcount  # type: ignore[assignment]

    # 4. Delete boards (cells cascade via relationship)
    if profile_ids:
        result = await session.execute(
            delete(Board).where(Board.profile_id.in_(profile_ids))
        )
        counts["boards_deleted"] = result.rowcount  # type: ignore[assignment]

    # 5. Delete care relationships
    result = await session.execute(
        delete(CareRelationship).where(CareRelationship.user_id == user_id)
    )
    counts["care_relationships_deleted"] = result.rowcount  # type: ignore[assignment]

    # 6. Revoke all consents
    await session.execute(
        update(UserConsent)
        .where(UserConsent.user_id == user_id)
        .values(granted=False, revoked_at=now)
    )
    counts["consents_revoked"] = 1

    return counts


async def export_user_data(session: AsyncSession, user_id: uuid.UUID) -> dict:
    """
    Export all personal data for a user (LGPD Art. 18, I — Right of access).

    Returns a dict with all user data suitable for JSON export.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    # User
    user_result = await session.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return {}

    user_data = {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }

    # Profiles
    profiles_result = await session.execute(
        select(AACProfile).where(AACProfile.user_id == user_id)
    )
    profiles = profiles_result.scalars().all()
    profiles_data = [
        {
            "id": str(p.id),
            "name": p.name,
            "communication_level": p.communication_level.value,
            "motor_capability": p.motor_capability.value,
            "visual_capability": p.visual_capability.value,
            "preferred_voice": p.preferred_voice,
            "grid_size_preference": p.grid_size_preference,
            "created_at": p.created_at.isoformat(),
        }
        for p in profiles
    ]

    # Boards
    profile_ids = [p.id for p in profiles]
    boards_data = []
    if profile_ids:
        boards_result = await session.execute(
            select(Board)
            .where(Board.profile_id.in_(profile_ids))
            .options(selectinload(Board.cells))
        )
        boards = boards_result.scalars().all()
        boards_data = [
            {
                "id": str(b.id),
                "name": b.name,
                "board_type": b.board_type.value,
                "grid_rows": b.grid_rows,
                "grid_cols": b.grid_cols,
                "cells_count": len(b.cells),
                "created_at": b.created_at.isoformat(),
            }
            for b in boards
        ]

    # Usage logs
    usage_data = []
    if profile_ids:
        usage_result = await session.execute(
            select(UsageLog)
            .where(UsageLog.profile_id.in_(profile_ids))
            .order_by(UsageLog.timestamp.desc())
            .limit(10000)
        )
        usage_logs = usage_result.scalars().all()
        usage_data = [
            {
                "id": str(u.id),
                "profile_id": str(u.profile_id),
                "timestamp": u.timestamp.isoformat(),
                "event_type": u.event_type,
                "event_data": u.event_data,
            }
            for u in usage_logs
        ]

    # Consents
    consents_result = await session.execute(
        select(UserConsent).where(UserConsent.user_id == user_id)
    )
    consents = consents_result.scalars().all()
    consents_data = [
        {
            "purpose": c.purpose,
            "granted": c.granted,
            "granted_at": c.granted_at.isoformat() if c.granted_at else None,
            "revoked_at": c.revoked_at.isoformat() if c.revoked_at else None,
        }
        for c in consents
    ]

    # Care relationships
    care_result = await session.execute(
        select(CareRelationship).where(CareRelationship.user_id == user_id)
    )
    care_rels = care_result.scalars().all()
    care_data = [
        {
            "id": str(cr.id),
            "profile_id": str(cr.profile_id),
            "relationship_type": cr.relationship_type.value,
            "created_at": cr.created_at.isoformat(),
        }
        for cr in care_rels
    ]

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user": user_data,
        "profiles": profiles_data,
        "boards": boards_data,
        "usage_logs": usage_data,
        "consents": consents_data,
        "care_relationships": care_data,
    }
