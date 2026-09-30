from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routes import router


app = FastAPI(
    title=settings.app_name,
    description="AI-powered comic generation application",
    version="1.0.0",
)


app.mount(
    "/static",
    StaticFiles(directory=str(settings.static_dir)),
    name="static",
)


app.include_router(router)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "app": settings.app_name,
        "gemini_flash_model": settings.gemini_flash_model,
        "local_image_model": settings.local_image_model,
    }