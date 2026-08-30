from fastapi import APIRouter

from app.schemas.schemas import HealthStatus

router = APIRouter()


@router.get("/health", response_model=HealthStatus)
def health() -> HealthStatus:
    return HealthStatus(status="ok")
