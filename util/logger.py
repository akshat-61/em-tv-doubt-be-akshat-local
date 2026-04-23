import json
import threading
from datetime import datetime, timezone

from util.config import LOG_FILE

_log_lock = threading.Lock()


def _write(record: dict):
    record["timestamp"] = datetime.now(timezone.utc).isoformat()
    line = json.dumps(record, ensure_ascii=False) + "\n"
    print(line.strip(), flush=True)
    with _log_lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)


def log_replied(video_id: str, username: str, message: str, reply: str):
    _write({
        "event":    "replied",
        "video_id": video_id,
        "user":     username,
        "message":  message,
        "reply":    reply,
    })


def log_skipped(video_id: str, username: str, message: str, reason: str):
    _write({
        "event":    "skipped",
        "video_id": video_id,
        "user":     username,
        "message":  message,
        "reason":   reason,
    })


def log_error(context: str, error: str):
    _write({
        "event":   "error",
        "context": context,
        "error":   error,
    })


def log_info(message: str, **kwargs):
    _write({"event": "info", "message": message, **kwargs})