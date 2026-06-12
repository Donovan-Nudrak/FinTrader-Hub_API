import uvicorn

from app.factory import create_app

app = create_app()


if __name__ == "__main__":
    from core.config import get_settings

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
    )
