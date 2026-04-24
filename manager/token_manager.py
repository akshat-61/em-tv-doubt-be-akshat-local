import json
import os
import threading
import requests
from datetime import datetime, timezone, timedelta

from util.config import TOKEN_FILE, YOUTUBE_CLIENT_SECRET_FILE

REFRESH_BUFFER_MINUTES = 5

_refresh_lock = threading.Lock()


def _load_token() -> dict:
    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError(
            f"[TokenManager] '{TOKEN_FILE}' not found. "
            "Run python oauth_setup.py first to authorise."
        )
    with open(TOKEN_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_token(token_data: dict):
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(token_data, f, indent=2)
    print("[TokenManager] token.json updated with new access token.")


def _load_client_secret() -> tuple[str, str]:
    if not os.path.exists(YOUTUBE_CLIENT_SECRET_FILE):
        raise FileNotFoundError(
            f"[TokenManager] '{YOUTUBE_CLIENT_SECRET_FILE}' not found. "
            "Download it from Google Cloud Console."
        )
    with open(YOUTUBE_CLIENT_SECRET_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    app = data.get("installed") or data.get("web")
    if not app:
        raise ValueError("[TokenManager] Unrecognised client_secret.json format.")

    return app["client_id"], app["client_secret"]


def _is_expired(token_data: dict) -> bool:
    expiry_str = token_data.get("expiry")
    if not expiry_str:
        return True
    try:
        expiry_str_clean = expiry_str.replace("Z", "+00:00")
        expiry_dt        = datetime.fromisoformat(expiry_str_clean)
        if expiry_dt.tzinfo is None:
            expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= (expiry_dt - timedelta(minutes=REFRESH_BUFFER_MINUTES))
    except (ValueError, TypeError):
        return True


def _refresh_access_token(token_data: dict) -> dict:
    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        raise ValueError(
            "[TokenManager] No refresh_token in token.json. "
            "Run python oauth_setup.py to re-authorise."
        )

    client_id, client_secret = _load_client_secret()

    print("[TokenManager] Access token expired — refreshing...")

    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id":     client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type":    "refresh_token",
        },
        timeout=10,
    )

    if response.status_code != 200:
        error_info = response.json()
        error_code = error_info.get("error", "unknown")
        if error_code in ("invalid_grant", "token_revoked"):
            raise PermissionError(
                "[TokenManager] refresh_token is invalid or revoked.\n"
                "Run: python oauth_setup.py"
            )
        raise RuntimeError(
            f"[TokenManager] Token refresh failed ({response.status_code}): {error_info}"
        )

    new_data   = response.json()
    expires_in = new_data.get("expires_in", 3600)
    new_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    token_data["token"]  = new_data["access_token"]
    token_data["expiry"] = new_expiry.isoformat()

    if "refresh_token" in new_data:
        token_data["refresh_token"] = new_data["refresh_token"]

    return token_data


def ensure_token_fresh():
    with _refresh_lock:
        token_data = _load_token()
        if not _is_expired(token_data):
            print("[TokenManager] Access token is still valid — no refresh needed.")
            return
        token_data = _refresh_access_token(token_data)
        _save_token(token_data)


def get_fresh_token() -> str:
    ensure_token_fresh()
    return _load_token()["token"]


if __name__ == "__main__":
    try:
        ensure_token_fresh()
        print("[TokenManager] Token check complete.")
    except (FileNotFoundError, PermissionError, RuntimeError, ValueError) as e:
        print(e)