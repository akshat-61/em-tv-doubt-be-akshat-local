from pymongo import MongoClient, errors
from datetime import datetime
from util.config import MONGODB_URI, MONGODB_DATABASE
from urllib.parse import quote_plus

client = None
db = None
live_sessions = None


class MongoDBClient:
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
    client = MongoDBClient()
    return client.get_collection(name)


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
    
 

def get_db():
    global client, db, live_sessions

    if client is None:
        try:
            client = MongoClient(
                MONGODB_URI["MONGO_URI"],
                serverSelectionTimeoutMS=5000
            )

            db = client[MONGODB_DATABASE]

            live_sessions = db["em_tv_live_sessions"]

        except errors.ServerSelectionTimeoutError as e:
            client = None
            raise

    return live_sessions

def generate_session_id():
    return "SESSION_" + datetime.now().strftime("%Y%m%d_%H%M%S")

def get_chat_collection_name():
    return "em_live_chat_" + datetime.utcnow().strftime("%d_%m_%Y")

def insert_live_session(channel_id, video_id, chat_room_id, live_video_link, title=""):
    sessions = get_db()
    existing = sessions.find_one({"video_id": video_id})

    if existing:
        return existing["session_id"]

    session_id = generate_session_id()
    collection_name = get_chat_collection_name()

    data = {
        "session_id": session_id,
        "channel_id": channel_id,
        "video_id": video_id,
        "chat_room_id": chat_room_id,
        "live_video_link": live_video_link,
        "collection_name": collection_name,
        "title": title,
        "status": "active",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "ended_at": None
    }

    sessions.insert_one(data)
    return session_id

def get_active_sessions():  
    return list(get_db().find({"status": "active"}))

def get_all_sessions():
    return list(get_db().find().sort("_id", -1))

def get_latest_active_session():
    return get_db().find_one({"status": "active"}, sort=[("_id", -1)])

def get_session_by_video_id(video_id):
    return get_db().find_one({"video_id": video_id})

def get_session_by_session_id(session_id):
    return get_db().find_one({"session_id": session_id})

def update_session_status(session_id, status):
    return get_db().update_one(
        {"session_id": session_id},
        {"$set": {"status": status, "updated_at": datetime.utcnow()}}
    )

def delete_session(session_id):
    return get_db().delete_one({"session_id": session_id})

def clear_all_sessions():
    return get_db().delete_many({})

def count_sessions():
    return get_db().count_documents({})

def end_session(video_id):
    return get_db().update_one(
        {"video_id": video_id},
        {"$set": {"status": "ended", "ended_at": datetime.utcnow(), "updated_at": datetime.utcnow()}}
    )