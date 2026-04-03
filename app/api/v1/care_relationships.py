import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DBSession
from app.models.aac_profile import AACProfile
from app.models.care_relationship import CareRelationship, RelationshipType
from app.models.user import User, UserRole
from app.schemas.care_relationship import (
    CareRelationshipCreate,
    CareRelationshipRead,
    InviteRequest,
    InviteResponse,
)

router = APIRouter()


def _to_read(rel: CareRelationship) -> CareRelationshipRead:
    """Converte CareRelationship ORM para CareRelationshipRead com dados aninhados."""
    user_name = rel.user.full_name if rel.user else None
    user_email = rel.user.email if rel.user else None
    profile_name = rel.profile.name if rel.profile else None
    return CareRelationshipRead(
        id=rel.id,
        user_id=rel.user_id,
        profile_id=rel.profile_id,
        relationship_type=rel.relationship_type,
        permissions=rel.permissions,
        created_at=rel.created_at,
        user_name=user_name,
        user_email=user_email,
        profile_name=profile_name,
    )


async def _check_profile_access(
    session, current_user: User, profile_id: uuid.UUID
) -> AACProfile:
    """Verifica se o usuário atual tem acesso ao perfil (dono, admin ou terapeuta vinculado)."""
    result = await session.execute(
        select(AACProfile).where(AACProfile.id == profile_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil não encontrado",
        )

    # Admin tem acesso total
    if current_user.role == UserRole.admin:
        return profile

    # Dono do perfil
    if profile.user_id == current_user.id:
        return profile

    # Terapeuta/cuidador vinculado
    rel_result = await session.execute(
        select(CareRelationship).where(
            CareRelationship.profile_id == profile_id,
            CareRelationship.user_id == current_user.id,
        )
    )
    if rel_result.scalar_one_or_none():
        return profile

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Sem permissão para acessar este perfil",
    )


@router.post("/", response_model=CareRelationshipRead, status_code=status.HTTP_201_CREATED)
async def create_relationship(
    data: CareRelationshipCreate,
    session: DBSession,
    current_user: CurrentUser,
) -> CareRelationshipRead:
    """Vincular um terapeuta/cuidador ao perfil de um paciente."""
    await _check_profile_access(session, current_user, data.profile_id)

    target_user_id = data.user_id
    if not target_user_id and data.email:
        # Buscar usuário pelo email
        result = await session.execute(
            select(User).where(User.email == data.email)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário com este email não encontrado",
            )
        target_user_id = user.id
    elif not target_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe user_id ou email",
        )

    # Verificar duplicidade
    existing = await session.execute(
        select(CareRelationship).where(
            CareRelationship.user_id == target_user_id,
            CareRelationship.profile_id == data.profile_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vínculo já existe",
        )

    rel = CareRelationship(
        user_id=target_user_id,
        profile_id=data.profile_id,
        relationship_type=data.relationship_type,
        permissions={},
    )
    session.add(rel)
    await session.flush()

    # Recarregar com relacionamentos
    result = await session.execute(
        select(CareRelationship)
        .options(selectinload(CareRelationship.user), selectinload(CareRelationship.profile))
        .where(CareRelationship.id == rel.id)
    )
    rel = result.scalar_one()
    return _to_read(rel)


@router.get("/", response_model=list[CareRelationshipRead])
async def list_relationships(
    session: DBSession,
    current_user: CurrentUser,
    profile_id: uuid.UUID | None = None,
) -> list[CareRelationshipRead]:
    """Listar vínculos de cuidado. Terapeutas veem seus pacientes, admins veem todos."""
    query = select(CareRelationship).options(
        selectinload(CareRelationship.user),
        selectinload(CareRelationship.profile),
    )

    if profile_id:
        query = query.where(CareRelationship.profile_id == profile_id)

    if current_user.role != UserRole.admin:
        # Não-admin só vê vínculos dos seus perfis ou onde é o terapeuta
        own_profiles = select(AACProfile.id).where(AACProfile.user_id == current_user.id)
        query = query.where(
            (CareRelationship.user_id == current_user.id)
            | (CareRelationship.profile_id.in_(own_profiles))
        )

    result = await session.execute(query)
    return [_to_read(r) for r in result.scalars().all()]


@router.get("/my-patients", response_model=list[CareRelationshipRead])
async def my_patients(
    session: DBSession,
    current_user: CurrentUser,
) -> list[CareRelationshipRead]:
    """Obter todos os perfis vinculados ao usuário atual (como terapeuta/cuidador)."""
    result = await session.execute(
        select(CareRelationship)
        .options(
            selectinload(CareRelationship.user),
            selectinload(CareRelationship.profile),
        )
        .where(CareRelationship.user_id == current_user.id)
    )
    return [_to_read(r) for r in result.scalars().all()]


@router.delete("/{relationship_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_relationship(
    relationship_id: uuid.UUID,
    session: DBSession,
    current_user: CurrentUser,
) -> None:
    """Remover um vínculo de cuidado."""
    result = await session.execute(
        select(CareRelationship).where(CareRelationship.id == relationship_id)
    )
    rel = result.scalar_one_or_none()
    if not rel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vínculo não encontrado",
        )

    # Verificar permissão: admin, dono do perfil, ou o próprio terapeuta
    if current_user.role != UserRole.admin:
        profile_result = await session.execute(
            select(AACProfile).where(AACProfile.id == rel.profile_id)
        )
        profile = profile_result.scalar_one_or_none()
        if not profile or (
            profile.user_id != current_user.id and rel.user_id != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sem permissão para remover este vínculo",
            )

    await session.delete(rel)
    await session.commit()


@router.post("/invite", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def invite_to_care(
    data: InviteRequest,
    session: DBSession,
    current_user: CurrentUser,
) -> InviteResponse:
    """Convidar um usuário para ser cuidador/terapeuta de um perfil."""
    await _check_profile_access(session, current_user, data.profile_id)

    # Verificar se o usuário já existe
    result = await session.execute(
        select(User).where(User.email == data.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        # Verificar se já existe vínculo
        existing_rel = await session.execute(
            select(CareRelationship).where(
                CareRelationship.user_id == existing_user.id,
                CareRelationship.profile_id == data.profile_id,
            )
        )
        if existing_rel.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este usuário já está vinculado a este perfil",
            )

        # Criar vínculo diretamente para usuários existentes
        rel = CareRelationship(
            user_id=existing_user.id,
            profile_id=data.profile_id,
            relationship_type=data.relationship_type,
            permissions={},
        )
        session.add(rel)
        await session.flush()
        await session.refresh(rel)

        return InviteResponse(
            id=rel.id,
            profile_id=data.profile_id,
            email=data.email,
            relationship_type=data.relationship_type,
            status="accepted",
            message=data.message,
        )

    # Usuário não existe — criar convite pendente
    # Em produção, enviaria email com link de cadastro
    invite_id = uuid.uuid4()
    return InviteResponse(
        id=invite_id,
        profile_id=data.profile_id,
        email=data.email,
        relationship_type=data.relationship_type,
        status="pending",
        message=data.message,
    )
