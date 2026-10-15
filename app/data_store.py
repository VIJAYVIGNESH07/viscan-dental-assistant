import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "data"


def _read_json(filename: str) -> list[dict[str, Any]]:
    path = DATA_DIR / filename
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_patients() -> list[dict[str, Any]]:
    return _read_json("patients.json")


def get_reports() -> list[dict[str, Any]]:
    return _read_json("reports.json")
