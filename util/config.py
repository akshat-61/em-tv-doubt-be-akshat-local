import os
from dotenv import load_dotenv


load_dotenv()

API_URL = os.getenv(
    "API_URL",
    "https://apigateway.extramarks.com/ai-chat/chat"
)

API_TIMEOUT = int(os.getenv("API_TIMEOUT", 15))

TOKEN_FILE = os.getenv("TOKEN_FILE", "data/token.json")
EXTRAMARKS_TOKEN_FILE = os.getenv(
    "EXTRAMARKS_TOKEN_FILE",
    "data/extramarks_token.json"
)
CHANNEL_ID = os.getenv("CHANNEL_ID", "")
MAX_STREAMS = int(os.getenv("MAX_STREAMS", 3))
USER_COOLDOWN_SECONDS = int(
    os.getenv("USER_COOLDOWN_SECONDS", 20)
)

POLL_INTERVAL_SECONDS = int(
    os.getenv("POLL_INTERVAL_SECONDS", 2)
)

STREAM_DISCOVERY_INTERVAL = int(
    os.getenv("STREAM_DISCOVERY_INTERVAL", 30)
)
SEEN_MSGS_FILE = os.getenv(
    "SEEN_MSGS_FILE",
    "data/seen_msgs.json"
)

STREAM_CONTEXT_FILE = os.getenv(
    "STREAM_CONTEXT_FILE",
    "data/topics.txt"
)
from urllib.parse import quote_plus

host = "10.172.3.7"
port = 27017
username = "chatsrvs_mongo"
password = "chat@456"
database = "chat_srvs"
authenticationDatabase = "admin"

MONGODB_URI = {
    "MONGO_URI" : f"mongodb://{username}:{quote_plus(password)}@{host}:{port}/{database}?authSource={authenticationDatabase}&readPreference=primary&directConnection=true&ssl=false"
}


MONGODB_DATABASE = database
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

LOG_FILE = os.getenv(
    "LOG_FILE",
    "app.log"
)

YOUTUBE_CLIENT_SECRET_FILE = os.getenv(
    "YOUTUBE_CLIENT_SECRET_FILE",
    "client_secret.json"
)

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID")
API_URL = os.getenv("API_URL")