from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logger import logger

# ============================================================
# API ROUTER IMPORTS
# ============================================================

from app.api.auth import router as auth_router
from app.api.workflow import router as workflow_router
from app.api.permission import router as permission_router
from app.api.audit import router as audit_router
from app.api.gates import router as gates_router

# AI Agent Router
from app.api.ai import router as ai_router

from app.api import staff

from app.api.staff_management import (
    router as staff_management_router,
)

# Staff Shift Management
from app.api.staff_shifts import (
    router as staff_shifts_router,
)

from app.api.weather import router as weather_router

from app.api.user_management import (
    router as user_management_router,
)

from app.api.flights import router as flights_router
from app.api.runways import router as runway_router

# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend APIs for Airport Operations Coordination",
)

# ============================================================
# CORS MIDDLEWARE
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# REGISTER API ROUTERS
# ============================================================

app.include_router(auth_router)
app.include_router(workflow_router)
app.include_router(permission_router)
app.include_router(audit_router)
app.include_router(gates_router)

# Staff Availability and Allocation
app.include_router(staff.router)

# Staff Management
app.include_router(staff_management_router)

# Staff Shift Management
app.include_router(staff_shifts_router)

# Weather Management
app.include_router(weather_router)

# Flight Operations
app.include_router(flights_router)

# User Management
app.include_router(user_management_router)

# AI Agent
app.include_router(ai_router)

app.include_router(runway_router)

# ============================================================
# HOME ENDPOINT
# ============================================================

@app.get("/")
def home():
    logger.info("Home endpoint accessed")

    return {
        "message": settings.app_name,
        "version": settings.app_version,
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():
    logger.info("Health check endpoint accessed")

    return {
        "status": "healthy",
    }