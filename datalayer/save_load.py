import json
from pathlib import Path
from typing import Dict, Optional

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SAVE_FILE = DATA_DIR / "session.json"


def has_session() -> bool:
    return SAVE_FILE.exists()


def save_session(state: Dict):
    with SAVE_FILE.open("w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)


def load_session() -> Optional[Dict]:
    if not SAVE_FILE.exists():
        return None
    with SAVE_FILE.open(encoding="utf-8") as fh:
        return json.load(fh)


def clear_session():
    if SAVE_FILE.exists():
        SAVE_FILE.unlink()

