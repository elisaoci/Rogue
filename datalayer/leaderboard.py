import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

LEADERBOARD_FILE = DATA_DIR / "leaderboard.json"
MAX_ENTRIES = 25


def load_leaderboard() -> List[Dict[str, Any]]:
    if not LEADERBOARD_FILE.exists():
        return []
    with LEADERBOARD_FILE.open(encoding="utf-8") as fh:
        return json.load(fh)


def record_attempt(entry: Dict[str, Any]):
    data = load_leaderboard()
    entry = dict(entry)
    entry["timestamp"] = datetime.utcnow().isoformat()
    data.append(entry)
    data.sort(key=lambda row: row.get("treasure", 0), reverse=True)
    trimmed = data[:MAX_ENTRIES]
    with LEADERBOARD_FILE.open("w", encoding="utf-8") as fh:
        json.dump(trimmed, fh, ensure_ascii=False, indent=2)

