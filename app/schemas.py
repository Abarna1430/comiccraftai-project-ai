from typing import List

from pydantic import BaseModel, Field


class PromptRequest(BaseModel):
    story_prompt: str = Field(..., min_length=3)
    character_name: str = "Milo"
    setting: str = "Enchanted Forest"
    tone: str = "Dramatic"
    art_style: str = "Comic Book"


class ComicPanel(BaseModel):
    panel_number: int
    scene_description: str
    dialogue: str = ""
    narration: str = ""
    image_prompt: str


class ComicOutline(BaseModel):
    title: str
    summary: str
    panels: List[ComicPanel]