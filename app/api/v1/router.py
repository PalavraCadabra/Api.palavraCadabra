from fastapi import APIRouter

from app.api.v1 import (
    ai,
    auth,
    backup,
    boards,
    privacy,
    profiles,
    symbols,
    sync,
    usage_logs,
    users,
)

api_v1_router = APIRouter()

api_v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(users.router, prefix="/users", tags=["users"])
api_v1_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
api_v1_router.include_router(boards.router, prefix="/boards", tags=["boards"])
api_v1_router.include_router(symbols.router, prefix="/symbols", tags=["symbols"])
api_v1_router.include_router(usage_logs.router, prefix="/usage-logs", tags=["usage-logs"])
api_v1_router.include_router(sync.router, prefix="/sync", tags=["sync"])
api_v1_router.include_router(backup.router, prefix="/backup", tags=["backup"])
api_v1_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_v1_router.include_router(privacy.router, prefix="/privacy", tags=["privacy"])
