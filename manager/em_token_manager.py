import json
import os
import base64
import time
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import util.logger as logger
from util.config import EXTRAMARKS_TOKEN_FILE

TOKEN_FILE             = EXTRAMARKS_TOKEN_FILE
REFRESH_BUFFER_MINUTES = 5          
LOGIN_TIMEOUT_SECONDS  = 10

LOGIN_URL = "https://apigateway.extramarks.com/cognito-login-service/auth/login?v=3"

LOGIN_HEADERS = {
    "authority":         "dev-apigateway.extramarks.com",
    "accept":            "application/json, text/plain, */*",
    "accept-language":   "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
    "client-id":         "INTERNAL",
    "content-type":      "application/json",
    "origin":            "https://sabdevx.extramarks.com",
    "referer":           "https://sabdevx.extramarks.com/",
    "sec-fetch-dest":    "empty",
    "sec-fetch-mode":    "cors",
    "sec-fetch-site":    "same-site",
    "token":             "",
    "user-agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    ),
}


def _require_env(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(
            f"[TokenManager] Missing required .env variable: {key}\n"
            f"Add it to your .env file and restart."
        )
    return val


def _build_login_payload() -> dict:
    return {
        "action":  "cognito_login",
        "apikey":  _require_env("EM_APIKEY"),
        "checksum": _require_env("EM_CHECKSUM"),
        "login_details": {
            "username":                 _require_env("EM_USERNAME"),
            "password":                 _require_env("EM_PASSWORD"),
            "app_name":                 "Teacher_App",
            "acess_id":                 "",
            "app_version":              "",
            "gcm_key":                  "",
            "email_address":            "",
            "latitude":                 "",
            "longitude":                "",
            "operating_system_version": "x86_64",
            "source":                   "website",
        },
        "enc_type":      1,
        "refresh_token": "",
    }


def _decode_jwt_exp(token: str) -> int | None:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        payload_b64 = parts[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding

        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        payload       = json.loads(payload_bytes)
        return payload.get("exp")
    except Exception:
        return None


def _is_token_expired(token: str) -> bool:
    exp = _decode_jwt_exp(token)
    if exp is None:
        return True

    buffer_ts = datetime.now(timezone.utc) + timedelta(minutes=REFRESH_BUFFER_MINUTES)
    exp_dt    = datetime.fromtimestamp(exp, tz=timezone.utc)

    if buffer_ts >= exp_dt:
        remaining = int((exp_dt - datetime.now(timezone.utc)).total_seconds())
        logger.log_info(f"[TokenManager] Token expires in {remaining}s — refreshing now.")
        return True

    remaining = int((exp_dt - datetime.now(timezone.utc)).total_seconds())
    logger.log_info(f"[TokenManager] Token valid for {remaining}s — no refresh needed.")
    return False


def _save_token(token: str):
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump({"token": token}, f, indent=2)
    logger.log_info(f"[TokenManager] Token saved to {TOKEN_FILE}")


def _load_token() -> str | None:
    if not os.path.exists(TOKEN_FILE):
        return None
    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("token")
    except Exception:
        return None


def _login() -> str:
    logger.log_info("[TokenManager] Logging in to Extramarks...")

    payload = _build_login_payload()

    try:
        response = requests.post(
            LOGIN_URL,
            headers=LOGIN_HEADERS,
            json=payload,
            timeout=LOGIN_TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("[TokenManager] Login request timed out.")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"[TokenManager] Login request failed: {e}")

    if response.status_code != 200:
        raise RuntimeError(
            f"[TokenManager] Login failed ({response.status_code}): {response.text[:300]}"
        )

    data = response.json()

    token = (
        data.get("token")
        or data.get("access_token")
        or data.get("id_token")
        or data.get("jwt")
        or (data.get("data") or {}).get("token")
        or (data.get("data") or {}).get("access_token")
    )

    if not token:
        raise RuntimeError(
            f"[TokenManager] Could not find token in login response.\n"
            f"Response keys: {list(data.keys())}\n"
            f"Full response: {json.dumps(data)[:500]}"
        )

    username = _require_env("EM_USERNAME")
    logger.log_info(f"[TokenManager] Login successful for '{username}'.")
    return token


def ensure_token_fresh():
    token = _load_token()

    if token and not _is_token_expired(token):
        return

    fresh = _login()
    _save_token(fresh)


def get_fresh_token() -> str:
    ensure_token_fresh()
    token = _load_token()
    if not token:
        raise RuntimeError("[TokenManager] Token unavailable after refresh attempt.")
    return token


if __name__ == "__main__":
    try:
        token = get_fresh_token()
        exp   = _decode_jwt_exp(token)
        exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc) if exp else None
        logger.log_info(f"[TokenManager] Token (first 60 chars): {token[:60]}...")
        if exp_dt:
            logger.log_info(f"[TokenManager] Expires at: {exp_dt.strftime('%d-%m-%Y %H:%M:%S UTC')}")
    except Exception as e:
        logger.log_error("TokenManager_Main", str(e))
