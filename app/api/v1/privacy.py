"""LGPD compliance endpoints — Data subject rights (Art. 18)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.models.consent import UserConsent
from app.services.anonymization import anonymize_user_data, export_user_data

router = APIRouter()


# --- Schemas ---


class ConsentUpdate(BaseModel):
    purpose: str  # communication, research, improvement, marketing
    granted: bool


class ConsentRead(BaseModel):
    purpose: str
    granted: bool
    granted_at: datetime | None
    revoked_at: datetime | None

    model_config = {"from_attributes": True}


# --- Endpoints ---


@router.get("/my-data")
async def get_personal_data(
    session: DBSession,
    current_user: CurrentUser,
) -> dict:
    """LGPD Art. 18, I — Right of access to personal data.

    Export ALL personal data associated with the authenticated user.
    """
    data = await export_user_data(session, current_user.id)
    return data


@router.delete("/my-data")
async def delete_personal_data(
    session: DBSession,
    current_user: CurrentUser,
) -> dict:
    """LGPD Art. 18, VI — Right to deletion of personal data.

    Anonymize/delete all personal data. Anonymized usage logs are kept
    for research purposes only if the user previously consented to research.
    """
    counts = await anonymize_user_data(session, current_user.id)
    return {
        "status": "data_anonymized",
        "detail": "Seus dados pessoais foram anonimizados/excluídos conforme LGPD Art. 18, VI.",
        "summary": counts,
    }


@router.post("/consent")
async def update_consent(
    data: ConsentUpdate,
    session: DBSession,
    current_user: CurrentUser,
    request: Request,
) -> ConsentRead:
    """LGPD Art. 8 — Consent management.

    Grant or revoke consent for a specific data processing purpose.
    """
    now = datetime.now(timezone.utc)

    # Find existing consent for this purpose
    result = await session.execute(
        select(UserConsent).where(
            UserConsent.user_id == current_user.id,
            UserConsent.purpose == data.purpose,
        )
    )
    consent = result.scalar_one_or_none()

    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")[:512]

    if consent:
        consent.granted = data.granted
        consent.ip_address = ip_address
        consent.user_agent = user_agent
        if data.granted:
            consent.granted_at = now
            consent.revoked_at = None
        else:
            consent.revoked_at = now
    else:
        consent = UserConsent(
            user_id=current_user.id,
            purpose=data.purpose,
            granted=data.granted,
            granted_at=now if data.granted else None,
            revoked_at=now if not data.granted else None,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        session.add(consent)

    await session.flush()
    await session.refresh(consent)
    return ConsentRead.model_validate(consent)


@router.get("/consent", response_model=list[ConsentRead])
async def get_consent(
    session: DBSession,
    current_user: CurrentUser,
) -> list[ConsentRead]:
    """Get current consent status for all purposes."""
    result = await session.execute(
        select(UserConsent).where(UserConsent.user_id == current_user.id)
    )
    consents = result.scalars().all()
    return [ConsentRead.model_validate(c) for c in consents]


@router.get("/data-processing")
async def data_processing_info() -> dict:
    """LGPD Art. 9 — Information about data processing.

    Public endpoint — no authentication required.
    """
    return {
        "controller": "palavraCadabra Tecnologia Assistiva LTDA",
        "dpo_contact": "dpo@palavracadabra.edu.br",
        "purposes": [
            {
                "purpose": "communication",
                "description": "Prover serviço de CAA",
                "legal_basis": "consent",
            },
            {
                "purpose": "research",
                "description": "Pesquisa científica anonimizada",
                "legal_basis": "consent",
                "optional": True,
            },
            {
                "purpose": "improvement",
                "description": "Melhoria do serviço",
                "legal_basis": "legitimate_interest",
            },
        ],
        "retention_period": (
            "Dados mantidos enquanto conta ativa. "
            "Excluídos em até 30 dias após solicitação."
        ),
        "international_transfer": (
            "Dados processados na AWS us-east-1 (EUA). "
            "Cláusulas contratuais padrão."
        ),
        "rights": [
            "access",
            "correction",
            "deletion",
            "portability",
            "opposition",
            "revocation",
        ],
    }
