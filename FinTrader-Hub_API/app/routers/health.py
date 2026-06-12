from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from core.config import get_settings
from infrastructure.cache import check_redis_connection
from infrastructure.database import check_database_connection
from infrastructure.database.schema_health import check_application_schema_ready

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> JSONResponse:
    settings = get_settings()
    services: dict[str, str] = {}
    all_healthy = True

    try:
        check_database_connection()
        services["postgresql"] = "connected"
    except Exception:
        services["postgresql"] = "disconnected"
        all_healthy = False

    try:
        check_redis_connection()
        services["redis"] = "connected"
    except Exception:
        services["redis"] = "disconnected"
        all_healthy = False

    if services.get("postgresql") == "connected":
        schema_status = check_application_schema_ready()
        services["migrations"] = schema_status["migrations"]
        services["schema"] = schema_status["schema"]
        if schema_status["migrations"] != "applied" or schema_status["schema"] != "ready":
            all_healthy = False
    else:
        services["migrations"] = "unknown"
        services["schema"] = "incomplete"

    payload = {
        "status": "healthy" if all_healthy else "unhealthy",
        "app": settings.app_name,
        "environment": settings.app_env,
        "services": services,
    }

    return JSONResponse(
        status_code=status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        content=payload,
    )
