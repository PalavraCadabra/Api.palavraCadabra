from fastapi import APIRouter

from app.api.v1 import auth, boards, profiles, symbols, users

api_v1_router = APIRouter()

api_v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(users.router, prefix="/users", tags=["users"])
api_v1_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
api_v1_router.include_router(boards.router, prefix="/boards", tags=["boards"])
api_v1_router.include_router(symbols.router, prefix="/symbols", tags=["symbols"])
