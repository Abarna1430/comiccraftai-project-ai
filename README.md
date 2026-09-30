# ComicCraft AI

ComicCraft AI is a Generative AI web application that converts a story idea into a five-panel comic.

## Features

- Story generation using Google Gemini
- Five-panel comic structure
- Character and setting customization
- Multiple tones
- Multiple art styles
- Free local AI image generation using an SDXL-based model
- Comic preview
- PDF export
- FastAPI backend
- Jinja2 frontend
- Environment-based API configuration

## Technologies

- Python
- FastAPI
- Uvicorn
- Jinja2
- Google Gemini API
- PyTorch and Diffusers
- Pillow
- FPDF2
- Pydantic

## Setup

Panel images are generated locally with `segmind/SSD-1B`; no image-generation API key or paid inference service is used. The first run downloads the model weights and needs an internet connection and several gigabytes of free disk space. An NVIDIA GPU is recommended; CPU generation is supported but substantially slower.

Create a virtual environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python run.py
```

Set `GEMINI_API_KEY` in `.env` for free-tier Gemini story generation. Gemini free-tier quotas still apply to story requests. Image generation uses the local model and does not require a Hugging Face token or Gemini image-model access.