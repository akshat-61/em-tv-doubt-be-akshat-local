from pymongo import MongoClient, ASCENDING, DESCENDING
from datetime import datetime
from util.config import MONGODB_URI, MONGODB_DATABASE

client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
db = client[MONGODB_DATABASE]


def get_chat_db():
    client.admin.command("ping")
    return db


def get_today_collection_name():
    return "em_tv_live_chat_" + datetime.utcnow().strftime("%d_%m_%Y")


def get_chat_collection(video_id=None):
    db = get_chat_db()

    collection_name = get_today_collection_name()
    # print("USING COLLECTION:", collection_name)

    collection = db[collection_name]

    collection.create_index([("chat_id", ASCENDING)], unique=True)
    collection.create_index([("video_id", ASCENDING)])
    collection.create_index([("created_at", DESCENDING)])

    return collection


def create_chat_id(video_id, message_id):
    return f"{video_id}_{message_id}"


def insert_youtube_chat(video_id, message_id, author_name, question, reply):
    collection = get_chat_collection(video_id)

    chat_id = create_chat_id(video_id, message_id)

    existing = collection.find_one({"chat_id": chat_id})

    if existing:
        return chat_id

    collection.insert_one({
        "chat_id": chat_id,
        "video_id": video_id,
        "message_id": message_id,
        "author_name": author_name,
        "question": question,
        "reply": reply,
        "answer": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })

    return chat_id