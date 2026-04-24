import json
import asyncio
from datetime import datetime
from bson import ObjectId
from urllib.parse import parse_qs
from fastapi import WebSocket, WebSocketDisconnect
from db.youtube_live_chats import get_chat_collection


clients = {}


def setup_websocket(app):

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()

        query = websocket.scope["query_string"].decode()
        params = parse_qs(query)

        video_id = params.get("userId", [None])[0]

        if video_id:
            clients[video_id] = websocket
            print(f"User connected: {video_id}")

            await send_db_questions(video_id)

            asyncio.create_task(live_push(video_id))

        try:
            while True:
                message = await websocket.receive_text()
                if not message or not message.strip():
                    print("Empty WS message")
                    continue

                try:
                    data = json.loads(message)

                except Exception:
                    print("Invalid JSON received:", message)
                    continue

                print("Received WS:", data)

                chat_id = (
                    data.get("chat_id")
                    or data.get("question_id")
                    or data.get("id")
                )

                answer = (
                    data.get("answer")
                    or data.get("reply")
                    or data.get("message")
                    or data.get("text")
                )

                if not chat_id or not answer:
                    print("Invalid payload:", data)
                    continue

                from app import send_reply, ReplyRequest

                try:
                    await asyncio.to_thread(
                        send_reply,
                        ReplyRequest(
                            question_id=str(chat_id),
                            reply=str(answer),
                            replied_by="akshat",
                            video_id=video_id
                        )
                    )

                    await websocket.send_json({
                        "success": True,
                        "message": "Reply processed"
                    })

                except Exception as e:
                    print("Reply Error:", str(e))

                    await websocket.send_json({
                        "success": False,
                        "error": str(e)
                    })

        except WebSocketDisconnect:
            print(f"Disconnected: {video_id}")

        finally:
            clients.pop(video_id, None)


async def send_db_questions(video_id):
    try:
        collection = get_chat_collection(video_id)

        print("Fetching old chats for:", video_id)
        print("Collection:", collection.name)

        chats = list(collection.find({}).sort("_id", 1))

        print("Total chats found:", len(chats))

        for chat in chats:
            print("Sending:", str(chat["_id"]))
            await send_chat(video_id, chat)

        print("All chats sent")

    except Exception as e:
        print("send_db_questions Error:", str(e))


async def live_push(video_id):
    last_id = None

    while video_id in clients:
        try:
            collection = get_chat_collection(video_id)

            query = {
                "type": {"$ne": "reply"}
            }

            if last_id:
                query["_id"] = {"$gt": last_id}

            chats = list(collection.find(query).sort("_id", 1))

            for chat in chats:
                last_id = chat["_id"]
                await send_chat(video_id, chat)

            await asyncio.sleep(2)

        except Exception as e:
            print("Live Push Error:", e)
            await asyncio.sleep(2)


async def send_chat(video_id, chat):
    if video_id in clients:
        await clients[video_id].send_json({
            "to": "akshat",
            "message": {
                "id": str(chat["_id"]),
                "username": chat.get("author_name", "@user"),
                "time": str(chat.get("created_at", "")),
                "text": chat.get("question", ""),
                "aiResponse": chat.get("reply", ""),
                "answer": chat.get("answer", "")
            }
        })