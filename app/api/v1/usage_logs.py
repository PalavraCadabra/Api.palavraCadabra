import uuid

from fastapi import APIRouter, Request, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.core.rate_limit import limiter
from app.models.usage_log import UsageLog
from app.schemas.usage_log import UsageLogCreate, UsageLogRead

router = APIRouter()


@router.post("/", response_model=UsageLogRead, status_code=status.HTTP_201_CREATED)
async def create_usage_log(
    data: UsageLogCreate,
    session: DBSession,
    current_user: CurrentUser,
) -> UsageLog:
    log = UsageLog(**data.model_dump(exclude_none=True))
    session.add(log)
    await session.flush()
    await session.refresh(log)
    return log


@router.post("/batch", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_usage_logs_batch(
    request: Request,
    data: list[UsageLogCreate],
    session: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Batch insert for syncing offline events."""
    logs = [UsageLog(**d.model_dump(exclude_none=True)) for d in data]
    session.add_all(logs)
    await session.flush()
    return {"count": len(logs)}


@router.get("/", response_model=list[UsageLogRead])
async def list_usage_logs(
    session: DBSession,
    current_user: CurrentUser,
    profile_id: uuid.UUID | None = None,
    event_type: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[UsageLog]:
    """List usage logs for a profile (for analytics)."""
    query = select(UsageLog)
    if profile_id:
        query = query.where(UsageLog.profile_id == profile_id)
    if event_type:
        query = query.where(UsageLog.event_type == event_type)
    query = query.order_by(UsageLog.timestamp.desc()).offset(skip).limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all())
