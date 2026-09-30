import re


def safe_filename(value: str) -> str:
    value = value.strip()

    value = re.sub(
        r"[^a-zA-Z0-9_\- ]+",
        "",
        value,
    )

    value = re.sub(
        r"\s+",
        "_",
        value,
    )

    return value[:80] or "comic"