import json
import re

from google import genai

from app.config import settings
from app.schemas import ComicOutline


def get_client():
    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    return genai.Client(
        api_key=settings.gemini_api_key
    )


def _extract_json(text: str) -> dict:
    text = text.strip()

    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
    )

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:
        return json.loads(text[start : end + 1])

    raise ValueError(
        "Gemini returned invalid JSON."
    )


def generate_story(
    outline: ComicOutline,
) -> ComicOutline:
    client = get_client()

    outline_json = outline.model_dump_json(
        indent=2
    )

    prompt = f"""
You are the final story editor for an AI comic.

Improve the following five-panel comic.

Rules:
- Keep exactly five panels.
- Keep the existing story.
- Make the narration concise.
- Make dialogue natural.
- Keep character consistency.
- Do not rewrite the image prompts unnecessarily.
- Return ONLY valid JSON.

Current comic:

{outline_json}

Return:

{{
  "title": "...",
  "summary": "...",
  "panels": [
    {{
      "panel_number": 1,
      "scene_description": "...",
      "dialogue": "...",
      "narration": "...",
      "image_prompt": "..."
    }}
  ]
}}
"""

    try:
        response = client.models.generate_content(
            model=settings.gemini_pro_model,
            contents=prompt,
        )

        if not response.text:
            return outline

        data = _extract_json(response.text)

        improved = ComicOutline.model_validate(data)

        if len(improved.panels) != 5:
            return outline

        return improved

    except Exception:
        # Story polishing is optional.
        # If it fails, retain the valid outline.
        return outline