from fastapi import APIRouter

from api.v1.endpoints.auth import router as auth_router
from api.v1.endpoints.users import router as users_router
from api.v1.endpoints.sessions import router as sessions_router
from api.v1.endpoints.dashboard import router as dashboard_router
from api.v1.endpoints.lessons import router as lessons_router
from api.v1.endpoints.p2p import router as p2p_router
from api.v1.endpoints.skills import router as skills_router
from api.v1.endpoints.leaderboard import router as leaderboard_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(sessions_router)
api_router.include_router(dashboard_router)
api_router.include_router(lessons_router)
api_router.include_router(p2p_router)
api_router.include_router(skills_router)
api_router.include_router(leaderboard_router)
