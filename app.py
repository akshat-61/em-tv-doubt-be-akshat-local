import json
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import re
from db.youtube_live_chats import get_chat_collection
from db.youtube_live_details import get_active_sessions, get_all_collections
from db.youtube_live_details import insert_live_session
from server import setup_websocket
from handler.chat_handler import start_bot
from core.ai_engine import validate_live_url
from bson import ObjectId
from datetime import datetime
from core.context_manager import _get_youtube_client
from db.youtube_live_details import get_session_by_video_id
from db.youtube_live_chats import get_chat_collection

app = FastAPI(title="YouTube Live Chat API")

setup_websocket(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LiveRequestModel(BaseModel):
    url: str 

@app.post("/api/live/start")
def start_live(request: LiveRequestModel):
    try:
        url = request.url.strip()

        match = re.search(
            r"(?:v=|youtu\.be/|live/|embed/)([a-zA-Z0-9_-]{11})",
            url
        )

        if not match:
            raise HTTPException(
                status_code=400,
                detail="Invalid YouTube URL"
            )

        input_video_id = match.group(1)

        validation = validate_live_url(url)

        if not validation["success"]:
            return validation

        session_id = insert_live_session(
            "manual",
            input_video_id,
            "room1",
            url,
            "Started from API"
        )
        print("🔥 Starting bot:", input_video_id)
        start_bot(input_video_id)

        return {
            "success": True,
            "message": "Live bot started successfully",
            "video_id": input_video_id,
            "session_id": session_id,
            "started_at": datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.get("/")
def home():
    return {
        "message": "FastAPI Server Running"
    }

class ReplyRequest(BaseModel):
    video_id: str
    question_id: str
    reply: str
    replied_by: str = "agent"

@app.post("/api/reply")
def send_reply(data: ReplyRequest):
    try:
        from db.youtube_live_chats import get_chat_collection
        from bson import ObjectId
        from datetime import datetime

        chat_collection = get_chat_collection(data.video_id)

        print("Reply Collection:", chat_collection.name)
        print("Incoming question_id:", data.question_id)

        query = {
            "$or": [
                {"chat_id": str(data.question_id)}
            ]
        }

        try:
            query["$or"].append(
                {"_id": ObjectId(str(data.question_id))}
            )
        except Exception:
            pass

        result = chat_collection.update_one(
            query,
            {
                "$set": {
                    "answer": str(data.reply),
                    "replied_by": str(data.replied_by),
                    "status": "replied",
                    "updated_at": datetime.utcnow()
                }
            }
        )

        if result.matched_count == 0:
            raise HTTPException(
                status_code=404,
                detail="Question not found"
            )

        youtube_sent = False
        youtube_error = None

        try:
            from core.youtube_reply import send_reply_to_youtube

            send_reply_to_youtube(
                data.video_id,
                data.question_id,
                data.reply
            )

            youtube_sent = True

        except Exception as e:
            youtube_error = str(e)
            print("YouTube Reply Error:", youtube_error)

        return {
            "success": True,
            "db_updated": True,
            "youtube_sent": youtube_sent,
            "youtube_error": youtube_error,
            "message": "Reply processed successfully"
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.get("/api/active-sessions")
def get_sessions():
    try:
        sessions = get_active_sessions()

        for session in sessions:
            session["_id"] = str(session["_id"])

            if session.get("created_at"):
                session["created_at"] = session["created_at"].isoformat()

            if session.get("updated_at"):
                session["updated_at"] = session["updated_at"].isoformat()

            if session.get("ended_at"):
                session["ended_at"] = session["ended_at"].isoformat()

        return {"sessions": sessions}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chats/{video_id}")
async def get_chats(video_id: str):
    try:
        colls = get_all_collections()

        for coll in colls:
            if coll["video_id"] == video_id:

                chats = coll["chats"]

                for chat in chats:
                    await send_question_to_frontend(
                        video_id,
                        str(chat.get("_id", "")),
                        chat.get("username", "@user"),
                        "12:35 pm",
                        chat.get("message", ""),
                        chat.get("aiResponse", "")

                    )

                return {"chats": coll}

        raise HTTPException(
            status_code=404,
            detail="No active session found"
        )

    except Exception as e:
        raise HTTPException(500, detail=str(e))

@app.get("/api/chats/stream/{video_id}")
def stream_chats(video_id: str):
    """
    Streams chats using Server Sent Events
    """

    def event_stream():
        try:
            chat_collection = get_chat_collection(video_id)

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        last_id = None

        try:
            initial_chats = list(
                chat_collection.find().sort("_id", -1).limit(50)
            )

            initial_chats.reverse()

            for chat in initial_chats:
                chat["_id"] = str(chat["_id"])

                if chat.get("created_at"):
                    chat["created_at"] = chat["created_at"].isoformat()

                if chat.get("updated_at"):
                    chat["updated_at"] = chat["updated_at"].isoformat()

                yield f"data: {json.dumps(chat)}\n\n"
                last_id = chat["_id"]

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        while True:
            query = {}

            if last_id:
                query = {
                    "_id": {
                        "$gt": ObjectId(last_id)
                    }
                }

            try:
                cursor = chat_collection.find(query).sort("_id", 1)

                for chat in cursor:
                    chat["_id"] = str(chat["_id"])

                    if chat.get("created_at"):
                        chat["created_at"] = chat["created_at"].isoformat()

                    if chat.get("updated_at"):
                        chat["updated_at"] = chat["updated_at"].isoformat()

                    yield f"data: {json.dumps(chat)}\n\n"
                    last_id = chat["_id"]

            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                return

            time.sleep(1)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )