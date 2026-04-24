import re
import uuid
import requests
import time
import util.logger as logger

from util.config import API_URL
from util.config import CHANNEL_ID
from util.config import YOUTUBE_API_KEY

from manager.em_token_manager import get_fresh_token

IGNORE_EXACT = {
    "lol", "hi", "hello", "ok", "nice", "wow", "🔥", "😂"
}

_API_TIMEOUT = 15


def extract_video_id(url: str):
    try:
        url = url.strip()

        match = re.search(
            r"(?:v=|youtu\.be/|live/|embed/)([a-zA-Z0-9_-]{11})",
            url
        )

        if match:
            return match.group(1)

        return None

    except Exception as e:
        logger.log_error("extract_video_id_error", str(e))
        return None


def validate_live_video(video_id):
    endpoint = "https://www.googleapis.com/youtube/v3/videos"

    params = {
        "part": "snippet,liveStreamingDetails",
        "id": video_id,
        "key": YOUTUBE_API_KEY
    }

    response = requests.get(endpoint, params=params)
    data = response.json()

    items = data.get("items", [])

    if not items:
        return False

    item = items[0]

    status = item["snippet"].get("liveBroadcastContent")

    if status == "live":
        return True

    return False

def validate_live_url(url: str):
    try:
        input_video_id = extract_video_id(url)

        if not input_video_id:
            return {
                "success": False,
                "message": "Invalid YouTube URL"
            }

        return {
            "success": True,
            "message": "Valid YouTube URL",
            "video_id": input_video_id
        }

    except Exception as e:
        logger.log_error("validate_live_url_error", str(e))
        return {
            "success": False,
            "message": str(e)
        }


def _fallback_classification(message: str):
    text = message.lower().strip()

    if not text:
        return "empty"

    if text in IGNORE_EXACT:
        return "normal"

    if text.startswith("@"):
        return "bot_message"

    if "http" in text or "www" in text:
        return "spam"

    if len(text.split()) < 2:
        return "short"

    if "?" in text:
        return "doubt"

    return "normal"


def _build_prompt(message: str, stream_context: str):
    return f"""
You are a YouTube live chat classifier.

Classify the message into only one label:

doubt
spam
greeting
normal
offtopic

Rules:
- Study related question = doubt
- Link promotion = spam
- Hi hello greetings = greeting
- Random unrelated = offtopic
- General normal text = normal

Stream Context:
{stream_context}

Message:
{message}

Return only one word label.
"""


def classify_message(message, stream_context=""):
    text = message.strip()

    if not text:
        return "empty"

    try:
        token = get_fresh_token()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

        payload = {
            "sender_uuid": str(uuid.uuid4()),
            "chat_room_id": 240,
            "message": _build_prompt(text, stream_context),
            "board_id": 180,
            "class_id": 1581786,
            "subject_id": 4900778,
            "message_id": str(uuid.uuid4())
        }

        response = None

        for attempt in range(3):
            try:
                response = requests.post(
                    API_URL,
                    headers=headers,
                    json=payload,
                    timeout=_API_TIMEOUT
                )

                if response.status_code == 200:
                    break

            except requests.exceptions.RequestException as e:
                logger.log_error(
                    "classification_retry",
                    f"Attempt {attempt+1} failed: {e}"
                )

                if attempt == 2:
                    raise

                time.sleep(1)

        if response and response.status_code == 200:
            data = response.json()

            result = (
            #     data.get("ai_response")
                data.get("response")
                or data.get("reply")
                or ""
            ).strip().lower()

            result = re.sub(r"[^a-z_ ]", "", result).strip()

            valid_labels = {
                "doubt",
                "spam",
                "greeting",
                "normal",
                "offtopic"
            }

            if result in valid_labels:
                return result

        return _fallback_classification(text)

    except Exception as e:
        logger.log_error("classification_error", str(e))
        return _fallback_classification(text)