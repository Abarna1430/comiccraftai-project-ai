from pathlib import Path

from app.schemas import ComicOutline


def build_comic_layout(
    outline: ComicOutline,
    image_paths: list[Path],
) -> list[dict]:

    panels = []

    for index, panel in enumerate(outline.panels):
        image_path = Path(image_paths[index])

        panels.append(
            {
                "panel_number": panel.panel_number,
                "scene_description": panel.scene_description,
                "dialogue": panel.dialogue,
                "narration": panel.narration,
                "image_prompt": panel.image_prompt,
                "image_path": image_path,
            }
        )

    return panels