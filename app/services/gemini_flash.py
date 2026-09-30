import json
import re

from google import genai

from app.config import settings
from app.schemas import ComicOutline


class GeminiQuotaError(RuntimeError):
    pass


def get_client():
    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. "
            "Add your Gemini API key to the .env file."
        )

    return genai.Client(
        api_key=settings.gemini_api_key
    )


def _extract_json(text: str) -> dict:
    text = text.strip()

    # Remove Markdown code fences if Gemini returns them.
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

    # Try direct JSON.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to locate the JSON object.
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:
        candidate = text[start : end + 1]

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise ValueError(
        "Gemini returned an invalid JSON response."
    )


def generate_outline(
    story_prompt: str,
    character_name: str,
    setting: str,
    tone: str,
    art_style: str,
) -> ComicOutline:
    client = get_client()

    prompt = f"""
You are the story planning engine for an AI comic generator.

Create a complete five-panel comic from the user's idea.

USER STORY:
{story_prompt}

MAIN CHARACTER:
{character_name}

SETTING:
{setting}

TONE:
{tone}

ART STYLE:
{art_style}

Requirements:

1. Exactly 5 chronological panels.
2. Define a fixed visual design for the main character, then repeat its identifying details verbatim in every image_prompt (species, colors, markings, eyes, clothing, and accessories).
3. Keep the main character visually consistent.
4. Each panel must move the story forward.
5. Create concise dialogue.
6. Create concise narration.
7. Create a detailed image prompt for each panel.
8. Image prompts must describe:
   - character appearance
   - action
   - environment
   - camera framing
   - lighting
   - mood
   - art style
9. Do not put dialogue text inside the generated image prompt.
10. Return ONLY valid JSON.

JSON format:

{{
  "title": "Comic title",
  "summary": "Short story summary",
  "panels": [
    {{
      "panel_number": 1,
      "scene_description": "Scene description",
      "dialogue": "Character dialogue",
      "narration": "Narrator text",
      "image_prompt": "Detailed image generation prompt"
    }}
  ]
}}
"""

    try:
        response = client.models.generate_content(
            model=settings.gemini_flash_model,
            contents=prompt,
        )

        if not response.text:
            raise RuntimeError(
                "Gemini returned an empty response."
            )

        data = _extract_json(response.text)

        outline = ComicOutline.model_validate(data)

        if len(outline.panels) != 5:
            raise ValueError(
                "Gemini did not generate exactly 5 panels."
            )
        if [panel.panel_number for panel in outline.panels] != [1, 2, 3, 4, 5]:
            raise ValueError(
                "Gemini panels must be numbered chronologically from 1 to 5."
            )

        return outline

    except Exception as exc:
        message = str(exc)

        if "429" in message or "RESOURCE_EXHAUSTED" in message:
            raise GeminiQuotaError(
                "Gemini story-generation quota is exhausted. Check the Google AI Studio project billing and rate limits for the configured model, then retry."
            ) from exc

        if "503" in message or "UNAVAILABLE" in message:
            raise RuntimeError(
                "Gemini is temporarily unavailable or "
                "experiencing high demand. Please try again "
                "after a short wait."
            ) from exc

        if "404" in message or "NOT_FOUND" in message:
            raise RuntimeError(
                f"Gemini model '{settings.gemini_flash_model}' "
                "was not found or is not available for this API key. "
                "Check GEMINI_FLASH_MODEL in .env."
            ) from exc

        if "401" in message or "403" in message:
            raise RuntimeError(
                "Gemini API authentication failed. "
                "Check GEMINI_API_KEY in .env."
            ) from exc

        raise RuntimeError(
            f"Gemini outline generation failed: {message}"
        ) from exc