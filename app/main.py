from fastapi import FastAPI

from app.config import settings
from app.logger import logger
from app.api.auth import router as auth_router
from app.api.workflow import router as workflow_router
from app.api.permission import router as permission_router
from app.api.audit import router as audit_router

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend APIs for Airport Operations Coordination"
)


app.include_router(auth_router)
app.include_router(workflow_router)
app.include_router(permission_router)
app.include_router(audit_router)

@app.get("/")
def home():
    logger.info("Home endpoint accessed")

    return {
        "message": settings.app_name,
        "version": settings.app_version
    }


@app.get("/health")
def health_check():
    logger.info("Health check endpoint accessed")

    return {
        "status": "healthy"
    }