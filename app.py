import json
import time
from bson import ObjectId
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import re
from db.youtube_live_chats import get_chat_collection
from db.youtube_live_details import get_active_sessions, get_all_collections
from server import setup_websocket
from db.youtube_live_details import insert_live_session
from core.ai_engine import validate_live_url
from core.ai_engine import validate_live_url
from server import setup_websocket

app = FastAPI(title="YouTube Live Chat API")
from datetime import datetime

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

# clients = {}


# def setup_websocket(app):

#     @app.websocket("/ws")
#     async def websocket_endpoint(websocket: WebSocket):
#         await websocket.accept()

#         query = websocket.scope["query_string"].decode()
#         params = parse_qs(query)

#         user_id = params.get("userId", [None])[0]

#         if user_id:
#             clients[user_id] = websocket
#             print(f"User connected: {user_id}")

#         try:
#             while True:
#                 message = await websocket.receive_text()
#                 data = json.loads(message)

#                 print("Received:", data)

#         except WebSocketDisconnect:
#             print(f"Client disconnected: {user_id}")

#         except Exception as e:
#             print(f"WebSocket error: {str(e)}")

#         finally:
#             if user_id in clients:
#                 del clients[user_id]


# async def send_question_to_frontend(
#     user_id,
#     question_id,
#     username,
#     time_text,
#     text,
#     ai_response=""
# ):
#     try:
#         if user_id in clients:
#             await clients[user_id].send_json({
#                 "to": "akshat",
#                 "message": {
#                     "id": question_id,
#                     "username": username,
#                     "time": time_text,
#                     "text": text,
#                     "aiResponse": ai_response
#                 }
#             })

#             return True

#         print(f"User not connected: {user_id}")
#         return False

#     except Exception as e:
#         print(f"Send error: {str(e)}")
#         return False

# async def send_question_to_frontend(user_id, chat_data):
#     if user_id in clients:

#         payload = {
#             "type": "question",
#             "id": chat_data.get("id"),
#             "username": chat_data.get("username"),
#             "time": datetime.now().strftime("%I:%M %p").lower(),
#             "text": chat_data.get("text"),
#             "aiResponse": chat_data.get("aiResponse", "")
#         }

#         await clients[user_id].send_json(payload)


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

        return {
            "success": True,
            "message": "Live bot started successfully",
            "video_id": input_video_id,
            "session_id": session_id,
            "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
        chat_collection = get_chat_collection(data.video_id)

        reply_doc = {
            "type": "reply",
            "chat_id": data.question_id,
            "message": data.reply,
            "replied_by": data.replied_by,
            "video_id": data.video_id,
            "status": "sent",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        result = chat_collection.insert_one(reply_doc)

        return {
            "success": True,
            "reply_id": str(result.inserted_id),
            "message": "Reply sent successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/active-sessions")
def get_sessions():
    """
    Return currently active live sessions
    """
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