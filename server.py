import json
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

        user_id = params.get("userId", [None])[0]

        if user_id:
            clients[user_id] = websocket
            print(f"User connected: {user_id}")

            # connect hote hi DB fetch + send
            await send_db_questions(user_id)

        try:
            while True:
                message = await websocket.receive_text()
                data = json.loads(message)

                print("Received:", data)

        except WebSocketDisconnect:
            print(f"Client disconnected: {user_id}")

        finally:
            if user_id in clients:
                del clients[user_id]


async def send_db_questions(video_id):
    try:
        collection = get_chat_collection(video_id)

        chats = list(collection.find({}).sort("_id", 1))

        for chat in chats:
            await clients[video_id].send_json({
                "to": "akshat",
                "message": {
                    "id": str(chat["_id"]),
                    "username": chat.get("author_name", "@user"),
                    "time": "12:35 pm",
                    "text": chat.get("question", ""),
                    "aiResponse": chat.get("reply", "")
                }
            })

        print("Questions sent to frontend")

    except Exception as e:
        print("Fetch Error:", str(e))