from threading import Lock
from pathlib import Path

from PIL import Image

from app.config import settings


_pipeline = None
_image_pipeline = None
_pipeline_lock = Lock()
_image_pipeline_lock = Lock()
_inference_lock = Lock()


def _get_pipeline():
    global _pipeline

    if _pipeline is not None:
        return _pipeline

    with _pipeline_lock:
        if _pipeline is not None:
            return _pipeline

        try:
            import torch
            from diffusers import AutoPipelineForText2Image
        except ImportError as exc:
            raise RuntimeError(
                "Local AI image generation requires PyTorch and Diffusers. Install the project dependencies with: python -m pip install -r requirements.txt"
            ) from exc

        use_cuda = torch.cuda.is_available()
        options = {
            "torch_dtype": torch.float16 if use_cuda else torch.float32,
            "use_safetensors": True,
        }
        if use_cuda:
            options["variant"] = "fp16"

        try:
            _pipeline = AutoPipelineForText2Image.from_pretrained(
                settings.local_image_model,
                **options,
            )
            if use_cuda:
                _pipeline.enable_model_cpu_offload()
            else:
                _pipeline.to("cpu")
            _pipeline.enable_attention_slicing()
            _pipeline.enable_vae_slicing()
        except Exception as exc:
            _pipeline = None
            raise RuntimeError(
                f"Could not load local AI model '{settings.local_image_model}'. The first run downloads the model; check internet access, disk space, and PyTorch compatibility. Details: {exc}"
            ) from exc

        return _pipeline


def _get_image_pipeline():
    global _image_pipeline

    if _image_pipeline is not None:
        return _image_pipeline

    with _image_pipeline_lock:
        if _image_pipeline is None:
            try:
                from diffusers import AutoPipelineForImage2Image
            except ImportError as exc:
                raise RuntimeError(
                    "Character consistency needs Diffusers image-to-image support. Install project dependencies with: python -m pip install -r requirements.txt"
                ) from exc

            _image_pipeline = AutoPipelineForImage2Image.from_pipe(
                _get_pipeline()
            )

    return _image_pipeline


def generate_image(
    prompt: str,
    output_path: Path,
    art_style: str = "Comic Book",
    character_reference: Path | None = None,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    final_prompt = (
        "Create one original landscape comic-book panel, not a page or collage. "
        f"Scene: {prompt}. Art direction: {art_style}; professional sequential comic illustration, "
        "cinematic composition, clearly readable action, richly detailed character and environment, "
        "expressive face, dramatic lighting, realistic shadows, polished ink and color. "
        "Maintain the exact same main character design described in the prompt."
    )

    try:
        pipeline = _get_pipeline()
        generation_options = {
            "prompt": final_prompt,
            "negative_prompt": (
                "text, lettering, captions, speech bubbles, watermark, logo, "
                "multiple panels, comic page layout, blurry, low detail, malformed anatomy"
            ),
            "width": 768,
            "height": 512,
            "num_inference_steps": 25,
            "guidance_scale": 6.5,
        }

        if character_reference is not None:
            reference_path = Path(character_reference)
            if not reference_path.is_file():
                raise RuntimeError(
                    f"Character reference image does not exist: {reference_path}"
                )
            final_prompt += (
                " The supplied prior panel is a visual reference for the protagonist; "
                "preserve the protagonist's identifying appearance while creating a new scene."
            )
            generation_options["prompt"] = final_prompt
            with Image.open(reference_path) as reference_image:
                generation_options["image"] = reference_image.convert("RGB")
            generation_options["strength"] = 0.78
            pipeline = _get_image_pipeline()

        with _inference_lock:
            result = pipeline(**generation_options)

        images = getattr(result, "images", None)
        if not images or not isinstance(images[0], Image.Image):
            raise RuntimeError("The local AI model returned no valid image.")

        images[0].convert("RGB").save(output_path, format="PNG")
        with Image.open(output_path) as saved_image:
            saved_image.verify()

        return output_path

    except Exception as exc:
        raise RuntimeError(f"Local AI image generation failed: {exc}") from exc