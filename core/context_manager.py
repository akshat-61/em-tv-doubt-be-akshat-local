import os

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials

import util.logger as logger
from util.config import TOKEN_FILE, STREAM_CONTEXT_FILE


def _get_youtube_client():
    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError(
            f"OAuth token not found at {TOKEN_FILE}. Run python oauth_setup.py first."
        )
    creds = Credentials.from_authorized_user_file(TOKEN_FILE)
    return build("youtube", "v3", credentials=creds)


def _load_custom_context() -> str:
    if not os.path.exists(STREAM_CONTEXT_FILE):
        return ""
    with open(STREAM_CONTEXT_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def _build_combined_context(title: str, description: str, custom: str) -> str:
    parts = []
    if title:
        parts.append(f"Stream title: {title}")
    if description:
        desc = description[:1500]
        if len(description) > 1500:
            desc += "... [trimmed]"
        parts.append(f"Stream description:\n{desc}")
    if custom:
        parts.append(f"Additional context from streamer:\n{custom}")
    return "\n\n".join(parts) if parts else "No stream context available."


def _empty_context() -> dict:
    return {
        "title":          "",
        "description":    "",
        "custom_context": "",
        "combined":       "No stream context available.",
    }


def get_stream_context(video_id: str) -> dict:
    try:
        youtube = _get_youtube_client()
        response = youtube.videos().list(
            part="snippet",
            id=video_id,
        ).execute()
    except (HttpError, FileNotFoundError) as e:
        logger.log_error(f"get_stream_context:{video_id}", str(e))
        return _empty_context()

    items = response.get("items", [])
    if not items:
        return _empty_context()

    snippet        = items[0]["snippet"]
    title          = snippet.get("title", "")
    description    = snippet.get("description", "")
    custom_context = _load_custom_context()
    combined       = _build_combined_context(title, description, custom_context)

    return {
        "title":          title,
        "description":    description,
        "custom_context": custom_context,
        "combined":       combined,
    }