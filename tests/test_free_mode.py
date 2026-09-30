from pathlib import Path
import pytest
from PIL import Image

from app.config import settings
from app.services.exporters import save_pdf
from app.services.image_generator import generate_image


def test_local_image_model_is_configured():
    assert settings.local_image_model


def test_local_image_generation_does_not_require_gemini_key(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    generated_image = Image.new("RGB", (48, 32), "green")
    calls = []

    class FakePipeline:
        def __call__(self, **kwargs):
            calls.append(kwargs)
            return type("Result", (), {"images": [generated_image]})()

    monkeypatch.setattr(
        "app.services.image_generator._get_pipeline",
        lambda: FakePipeline(),
    )

    output_path = tmp_path / "generated.png"
    result = generate_image(
        prompt="A red fox opens a glowing tree door",
        output_path=output_path,
    )

    assert result == output_path
    with Image.open(result) as image:
        assert image.format == "PNG"
        assert image.size == (48, 32)
    assert "red fox" in calls[0]["prompt"]
    assert calls[0]["num_inference_steps"] == 25


def test_local_image_generation_errors_are_not_replaced_by_placeholders(
    tmp_path: Path,
    monkeypatch,
):
    class BrokenPipeline:
        def __call__(self, **kwargs):
            raise RuntimeError("test model failure")

    monkeypatch.setattr(
        "app.services.image_generator._get_pipeline",
        lambda: BrokenPipeline(),
    )

    output_path = tmp_path / "failed.png"
    with pytest.raises(RuntimeError, match="test model failure"):
        generate_image("A fox in a forest", output_path)

    assert not output_path.exists()


def test_pdf_export_works_for_panel_images(tmp_path: Path):
    image_path = tmp_path / "panel.png"
    Image.new("RGB", (50, 50), "white").save(image_path)

    pdf_path = tmp_path / "comic.pdf"
    save_pdf(
        title="Test Comic",
        summary="A short test summary",
        panels=[
            {
                "panel_number": 1,
                "image_path": str(image_path),
                "scene_description": "A hero looks ahead.",
                "narration": "The journey begins.",
                "dialogue": "Hero: Let's go!",
            }
        ],
        output_path=pdf_path,
    )

    assert pdf_path.exists()
    assert pdf_path.suffix.lower() == ".pdf"
