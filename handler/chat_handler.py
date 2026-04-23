import time
import threading
import queue
import datetime

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

import util.logger as logger
from core.ai_engine import classify_message
from core.context_manager import get_stream_context
from db.youtube_live_chats import insert_youtube_chat
from db.youtube_live_details import get_active_sessions
from util.config import (
    USER_COOLDOWN_SECONDS,
    TOKEN_FILE,
)

_seen_msgs = {}
_seen_msgs_lock = threading.Lock()

_user_cooldowns = {}
_cooldowns_lock = threading.Lock()

_active_threads = {}
_threads_lock = threading.Lock()

_stream_context_cache = {}
_context_lock = threading.Lock()

_token_lock = threading.Lock()

shutdown_event = threading.Event()
message_queue = queue.Queue(maxsize=1000)


def _get_youtube_client():
    with _token_lock:
        creds = Credentials.from_authorized_user_file(TOKEN_FILE)

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def _mark_seen(video_id, msg_id):
    with _seen_msgs_lock:
        if video_id not in _seen_msgs:
            _seen_msgs[video_id] = set()

        if msg_id in _seen_msgs[video_id]:
            return False

        _seen_msgs[video_id].add(msg_id)
        return True


def _get_stream_context(video_id):
    with _context_lock:
        if video_id in _stream_context_cache:
            return _stream_context_cache[video_id]

    ctx = get_stream_context(video_id)

    with _context_lock:
        _stream_context_cache[video_id] = ctx

    return ctx


def _fetch_messages_worker(video_id):
    yt = _get_youtube_client()

    res = yt.videos().list(
        part="liveStreamingDetails",
        id=video_id
    ).execute()

    items = res.get("items", [])

    if not items:
        logger.log_error("fetch_messages", f"video not found: {video_id}")
        return

    chat_id = items[0]["liveStreamingDetails"].get("activeLiveChatId")

    if not chat_id:
        logger.log_error("fetch_messages", f"no active chat id: {video_id}")
        return

    ctx = _get_stream_context(video_id)["combined"]

    while not shutdown_event.is_set():
        try:
            res = yt.liveChatMessages().list(
                liveChatId=chat_id,
                part="snippet,authorDetails"
            ).execute()

            for msg in res.get("items", []):
                msg_id = msg["id"]

                if not _mark_seen(video_id, msg_id):
                    continue

                try:
                    message_queue.put((video_id, msg, ctx), timeout=1)
                except queue.Full:
                    pass

            time.sleep(2)

        except Exception as e:
            logger.log_error("fetch_messages", str(e))
            time.sleep(5)


def _process_messages_worker():
    while not shutdown_event.is_set():
        try:
            try:
                video_id, msg, ctx = message_queue.get(timeout=1)
            except queue.Empty:
                continue

            username = msg["authorDetails"]["displayName"]
            text = msg["snippet"]["displayMessage"]
            message_id = msg["id"]

            now = time.time()

            with _cooldowns_lock:
                if video_id not in _user_cooldowns:
                    _user_cooldowns[video_id] = {}

                last = _user_cooldowns[video_id].get(username, 0)

            if now - last < USER_COOLDOWN_SECONDS:
                continue

            if text.startswith("@"):
                continue

            classification = classify_message(text, ctx)

            insert_youtube_chat(
                video_id=video_id,
                message_id=message_id,
                author_name=username,
                question=text,
                reply=classification
            )

            with _cooldowns_lock:
                _user_cooldowns[video_id][username] = now

        except Exception as e:
            logger.log_error("process_messages", str(e))
            time.sleep(2)


def start_bot(video_id):
    with _threads_lock:
        if video_id in _active_threads:
            return

        t = threading.Thread(
            target=_fetch_messages_worker,
            args=(video_id,),
            daemon=True
        )

        _active_threads[video_id] = t
        t.start()

    for _ in range(3):
        threading.Thread(
            target=_process_messages_worker,
            daemon=True
        ).start()


def stop_bot(video_id):
    with _threads_lock:
        if video_id in _active_threads:
            del _active_threads[video_id]

def run():
    while not shutdown_event.is_set():
        try:
            sessions = get_active_sessions()
            for session in sessions:
                vid = session.get("video_id")
                if vid:
                    start_bot(vid)
            
            for _ in range(30):
                if shutdown_event.is_set():
                    break
                time.sleep(1)
        except Exception as e:
            logger.log_error("run_loop", str(e))
            time.sleep(30)