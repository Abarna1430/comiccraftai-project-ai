from pathlib import Path

from fpdf import FPDF


def clean_text(value: str) -> str:
    """
    Convert text into a form that the built-in PDF fonts
    can safely handle.
    """
    return (
        value
        .replace("—", "-")
        .replace("–", "-")
        .replace("’", "'")
        .replace("“", '"')
        .replace("”", '"')
        .encode("latin-1", "replace")
        .decode("latin-1")
    )


def save_pdf(
    title: str,
    summary: str,
    panels: list[dict],
    output_path: Path,
) -> Path:

    output_path = Path(output_path)

    pdf = FPDF(
        orientation="P",
        unit="mm",
        format="A4",
    )

    pdf.set_auto_page_break(
        auto=True,
        margin=15,
    )

    # -------------------------------------------------
    # Cover page
    # -------------------------------------------------

    pdf.add_page()

    pdf.set_font(
        "Helvetica",
        "B",
        24,
    )

    pdf.multi_cell(
        190,
        14,
        clean_text(title),
        align="C",
    )

    pdf.ln(8)

    pdf.set_font(
        "Helvetica",
        "",
        12,
    )

    pdf.multi_cell(
        190,
        8,
        clean_text(summary),
        align="C",
    )

    # -------------------------------------------------
    # Panels
    # -------------------------------------------------

    for panel in panels:

        pdf.add_page()

        pdf.set_font(
            "Helvetica",
            "B",
            16,
        )

        pdf.cell(
            190,
            10,
            f"Panel {panel['panel_number']}",
            new_x="LMARGIN",
            new_y="NEXT",
        )

        image_path = Path(
            panel["image_path"]
        )

        if image_path.exists():

            pdf.image(
                str(image_path),
                x=15,
                y=30,
                w=180,
            )

            pdf.set_y(140)

        pdf.set_font(
            "Helvetica",
            "B",
            11,
        )

        pdf.multi_cell(
            190,
            7,
            "Scene:",
        )

        pdf.set_font(
            "Helvetica",
            "",
            10,
        )

        pdf.multi_cell(
            190,
            6,
            clean_text(
                panel["scene_description"]
            ),
        )

        pdf.ln(3)

        pdf.set_font(
            "Helvetica",
            "B",
            11,
        )

        pdf.multi_cell(
            190,
            7,
            "Narration:",
        )

        pdf.set_font(
            "Helvetica",
            "",
            10,
        )

        pdf.multi_cell(
            190,
            6,
            clean_text(
                panel["narration"]
            ),
        )

        pdf.ln(3)

        pdf.set_font(
            "Helvetica",
            "B",
            11,
        )

        pdf.multi_cell(
            190,
            7,
            "Dialogue:",
        )

        pdf.set_font(
            "Helvetica",
            "",
            10,
        )

        pdf.multi_cell(
            190,
            6,
            clean_text(
                panel["dialogue"]
            ),
        )

    pdf.output(str(output_path))

    return output_path