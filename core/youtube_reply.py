from core.context_manager import _get_youtube_client
from db.youtube_live_details import get_db


def send_reply_to_youtube(video_id, question_id, reply_text):
    youtube = _get_youtube_client()

    # STEP 1: Fresh active live chat id fetch karo
    response = youtube.videos().list(
        part="liveStreamingDetails",
        id=video_id
    ).execute()

    items = response.get("items", [])

    if not items:
        raise Exception("Video not found")

    live_details = items[0].get("liveStreamingDetails", {})
    live_chat_id = live_details.get("activeLiveChatId")

    if not live_chat_id:
        raise Exception("No active live chat found")

    # STEP 2: DB me latest chat_room_id update karo
    sessions = get_db()

    sessions.update_one(
        {"video_id": video_id},
        {
            "$set": {
                "chat_room_id": live_chat_id
            }
        }
    )

    # STEP 3: Message send karo
    result = youtube.liveChatMessages().insert(
        part="snippet",
        body={
            "snippet": {
                "liveChatId": live_chat_id,
                "type": "textMessageEvent",
                "textMessageDetails": {
                    "messageText": reply_text
                }
            }
        }
    ).execute()

    print("YouTube Reply Sent:", result)

    return result