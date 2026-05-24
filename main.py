from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.config import settings
from core.database import init_db
from api.v1.router import api_router
from services.nb_service import schedule_daily_check


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    scheduler = schedule_daily_check()
    scheduler.start()
    yield
    # Shutdown
    scheduler.shutdown(wait=False)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="EduMentor AI - AI-powered student support platform",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "project": settings.PROJECT_NAME, "version": settings.VERSION}


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}
