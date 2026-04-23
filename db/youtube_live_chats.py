from pymongo import MongoClient, ASCENDING, errors
from datetime import datetime
import util.logger as logger
from util.config import MONGODB_URI, MONGODB_DATABASE
from db.youtube_live_details import get_db as get_sessions_db
from urllib.parse import quote_plus

client = None
db = None 


class  MongoDBClient:
    _instance = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            try:
                host = "10.172.3.7"
                port = 27017
                username = "chatsrvs_mongo"
                password = "chat@456"
                database = "chat_srvs"
                authenticationDatabase = "admin"

                password1 = quote_plus(password)
                # host = mongoHost
                # port = mongoPort
                # database = mongoDatabase
                # username = mongoUser
                authSource = authenticationDatabase
                uri = f"mongodb://{username}:{password1}@{host}:{port}/{database}?authSource={authSource}&readPreference=primary&directConnection=true&ssl=false"
                client = MongoClient(uri)
                cls._instance._db = client[database]
            except Exception as e:
                raise
        return cls._instance

    def get_collection(self, name):
        return self._db[name]

def get_collection(name):
    return MongoClient().get_collection(name)
    
def save():
    collection = get_collection("em_tv_live_sessions")
    collection.insert_one({"video_id": "test_video_id", "title": "test_title", "status": "active", "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(), "ended_at": None})

def get_all_collections():
    collection = get_collection("em_tv_live_sessions")
    docs = list(collection.find({}))
    return [serialize_doc(doc) for doc in docs]

def serialize_doc(doc):
    doc["_id"] = str(doc["_id"])
    return doc
    
def get_chat_db():
    global client, db
    if client is None:
        try:
            uri = MONGODB_URI["MONGO_URI"]
            print("mongo uri",uri)
            client = MongoClient(MONGODB_URI["MONGO_URI"], serverSelectionTimeoutMS=5000)
            db = client[MONGODB_DATABASE]
        except errors.ServerSelectionTimeoutError as e:
            client = None
            raise
    return db

def get_chat_collection(video_id):
    db = get_chat_db()

    sessions_collection = db["em_tv_live_sessions"]
    session = sessions_collection.find_one({"video_id": video_id})

    if not session:
        raise Exception(f"Live session not found for this video_id: {video_id}")

    collection_name = f"em_tv_live_chat_{video_id}"
    return db[collection_name]

def create_chat_id(video_id, message_id):
    return f"{video_id}_{message_id}"

def get_chat_collection_name(collection_name):
    return f"em_tv_live_chat_{collection_name}"


def insert_youtube_chat(
    video_id,
    message_id,
    author_name,
    question,
    reply,
    created_at=None
):
    chat_messages = get_chat_collection(video_id)
    chat_id = create_chat_id(video_id, message_id)

    existing = chat_messages.find_one({"chat_id": chat_id})

    if existing:
        return chat_id

    data = {
        "chat_id": chat_id,
        "video_id": video_id,
        "author_name": author_name,
        "question": question,
        "reply": reply,
        "answer": None,
        "ai_response": False,
        "created_at": created_at or datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    chat_messages.insert_one(data)
    return chat_id

def get_chat_by_id(video_id, chat_id):
    chat_messages = get_chat_collection(video_id)
    return chat_messages.find_one({"chat_id": chat_id})

def get_question_answer(video_id, question):
    chat_messages = get_chat_collection(video_id)
    return chat_messages.find_one({"question": question})

def get_video_chats(video_id):
    chat_messages = get_chat_collection(video_id)
    return list(chat_messages.find({"video_id": video_id}).sort("_id", -1))

def count_total_chats(video_id):
    chat_messages = get_chat_collection(video_id)
    return chat_messages.count_documents({})

def clear_chat_collection(video_id):
    chat_messages = get_chat_collection(video_id)
    return chat_messages.delete_many({})


#Checks ONLY

# if __name__ == "__main__":
#     try:
#         db = get_chat_db()
#         print("✅ MongoDB Connected")
#         print("Database:", db.name)
#         print("Collections:", db.list_collection_names())
#     except Exception as e:
#         print("❌ Connection Failed:", e)