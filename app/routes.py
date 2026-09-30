from pathlib import Path
import traceback
from uuid import uuid4

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.schemas import PromptRequest
from app.services.exporters import save_pdf
from app.services.gemini_flash import (
    GeminiQuotaError,
    generate_outline,
)
from app.services.gemini_pro import generate_story
from app.services.image_generator import generate_image
from app.services.layout_builder import build_comic_layout
from app.utils.files import safe_filename


router = APIRouter()

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": settings.app_name,
        },
    )


@router.post("/generate", response_class=HTMLResponse)
async def generate_comic(
    request: Request,
    story_prompt: str = Form(None),
    prompt: str = Form(None),
    character_name: str = Form("Milo"),
    setting: str = Form("Enchanted Forest"),
    tone: str = Form("Dramatic"),
    art_style: str = Form(None),
    style: str = Form(None),
):
    try:
        actual_prompt = (story_prompt or prompt or "").strip()
        actual_style = (art_style or style or "Comic Book").strip()

        if not actual_prompt:
            raise ValueError("Story prompt is required.")

        data = PromptRequest(
            story_prompt=actual_prompt,
            character_name=character_name or "Milo",
            setting=setting or "Enchanted Forest",
            tone=tone or "Dramatic",
            art_style=actual_style,
        )

        # -------------------------------------------------
        # 1. Generate the comic outline
        # -------------------------------------------------
        outline = generate_outline(
            story_prompt=data.story_prompt,
            character_name=data.character_name,
            setting=data.setting,
            tone=data.tone,
            art_style=data.art_style,
        )

        # -------------------------------------------------
        # 2. Refine story with narration and dialogue
        # -------------------------------------------------
        try:
            improved_outline = generate_story(outline)
        except Exception as story_exc:
            traceback.print_exc()
            improved_outline = outline

        # -------------------------------------------------
        # 3. Generate panel images
        # -------------------------------------------------
        comic_id = uuid4().hex[:10]
        image_paths = []

        for index, panel in enumerate(improved_outline.panels, start=1):
            filename = f"{comic_id}_panel_{index}.png"
            image_path = settings.generated_dir / filename

            generated_path = generate_image(
                prompt=panel.image_prompt,
                output_path=image_path,
                art_style=data.art_style,
                character_reference=image_paths[0] if image_paths else None,
            )

            image_paths.append(generated_path)

        # -------------------------------------------------
        # 4. Build layout information
        # -------------------------------------------------
        panels = build_comic_layout(
            outline=improved_outline,
            image_paths=image_paths,
        )

        # -------------------------------------------------
        # 5. Export PDF
        # -------------------------------------------------
        pdf_filename = (
            safe_filename(improved_outline.title)
            + "_"
            + comic_id
            + ".pdf"
        )
        pdf_path = settings.exports_dir / pdf_filename

        save_pdf(
            title=improved_outline.title,
            summary=improved_outline.summary,
            panels=panels,
            output_path=pdf_path,
        )

        image_urls = [
            f"/static/generated/{Path(path).name}"
            for path in image_paths
        ]

        return templates.TemplateResponse(
            request=request,
            name="comic_preview.html",
            context={
                "app_name": settings.app_name,
                "outline": improved_outline,
                "panels": panels,
                "layout": panels,
                "image_urls": image_urls,
                "pdf_url": f"/download/{pdf_filename}",
                "pdf_path": str(pdf_path),
            },
        )

    except Exception as exc:
        traceback.print_exc()
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={
                "app_name": settings.app_name,
                "error": str(exc),
            },
            status_code=500,
        )


@router.post("/generate-comic/json")
async def generate_comic_json(data: PromptRequest):
    try:
        if not data.story_prompt.strip():
            raise HTTPException(
                status_code=400,
                detail="Story prompt is required.",
            )

        # 1. Generate outline
        outline = generate_outline(
            story_prompt=data.story_prompt,
            character_name=data.character_name,
            setting=data.setting,
            tone=data.tone,
            art_style=data.art_style,
        )

        # 2. Refine story with Gemini Pro
        try:
            improved_outline = generate_story(outline)
        except Exception:
            improved_outline = outline

        # 3. Generate images
        comic_id = uuid4().hex[:10]
        image_paths = []

        for index, panel in enumerate(improved_outline.panels, start=1):
            filename = f"{comic_id}_panel_{index}.png"
            image_path = settings.generated_dir / filename

            generated_path = generate_image(
                prompt=panel.image_prompt,
                output_path=image_path,
                art_style=data.art_style,
                character_reference=image_paths[0] if image_paths else None,
            )
            image_paths.append(generated_path)

        # 4. Build layout
        panels = build_comic_layout(
            outline=improved_outline,
            image_paths=image_paths,
        )

        # 5. Save PDF
        pdf_filename = (
            safe_filename(improved_outline.title)
            + "_"
            + comic_id
            + ".pdf"
        )
        pdf_path = settings.exports_dir / pdf_filename

        save_pdf(
            title=improved_outline.title,
            summary=improved_outline.summary,
            panels=panels,
            output_path=pdf_path,
        )

        return {
            "status": "success",
            "comic_id": comic_id,
            "title": improved_outline.title,
            "summary": improved_outline.summary,
            "panels": [
                {
                    "panel_number": p["panel_number"],
                    "scene_description": p["scene_description"],
                    "dialogue": p["dialogue"],
                    "narration": p["narration"],
                    "image_prompt": p["image_prompt"],
                    "image_url": f"/static/generated/{Path(p['image_path']).name}",
                    "image_path": str(p["image_path"]),
                }
                for p in panels
            ],
            "layout": [
                {
                    "panel_number": p["panel_number"],
                    "scene_description": p["scene_description"],
                    "dialogue": p["dialogue"],
                    "narration": p["narration"],
                    "image_prompt": p["image_prompt"],
                    "image_url": f"/static/generated/{Path(p['image_path']).name}",
                }
                for p in panels
            ],
            "pdf_url": f"/download/{pdf_filename}",
            "pdf_path": str(pdf_path),
        }

    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/export-success", response_class=HTMLResponse)
async def export_success(
    request: Request,
    pdf_path: str = "",
    pdf_url: str = "",
):
    download_url = pdf_url or (f"/download/{Path(pdf_path).name}" if pdf_path else "")
    return templates.TemplateResponse(
        request=request,
        name="export_success.html",
        context={
            "app_name": settings.app_name,
            "pdf_path": pdf_path,
            "pdf_url": download_url,
        },
    )


@router.get("/test-image")
async def test_image(
    prompt: str = "A futuristic city at sunset, sci-fi, cinematic, artstation",
):
    try:
        comic_id = uuid4().hex[:10]
        test_path = settings.generated_dir / f"test_{comic_id}.png"
        image_path = generate_image(
            prompt=prompt,
            output_path=test_path,
        )
        return {
            "message": "Image generated successfully",
            "path": str(image_path),
            "url": f"/static/generated/{test_path.name}",
        }
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/download/{filename}")
async def download_pdf(filename: str):
    safe_name = Path(filename).name
    file_path = settings.exports_dir / safe_name

    if not file_path.exists():
        return HTMLResponse(
            content="PDF file not found.",
            status_code=404,
        )

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=safe_name,
    )
