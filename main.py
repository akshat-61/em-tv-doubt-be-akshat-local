import sys
import os
import time
from util import config
from handler.chat_handler import run, shutdown_event
from core.topic_parser import parse_text_to_json
import util.logger as logger

if __name__ == "__main__":
    # Ensure data directory exists
    if not os.path.exists("data"):
        os.makedirs("data")

    # The original code looked for topics.txt in root
    # Since I deleted it, I'll check data/topics.json instead or provide a fallback
    if os.path.exists("topics.txt"):
        parse_text_to_json("topics.txt", "data/topics.json")
    elif os.path.exists("data/topics.txt"):
         parse_text_to_json("data/topics.txt", "data/topics.json")

    try:
        # Validate config
        _ = config.CHANNEL_ID
        _ = config.API_URL
        _ = config.YOUTUBE_CLIENT_SECRET_FILE
    except EnvironmentError as e:
        print(f"[Startup Error] {e}")
        sys.exit(1)

    try:
        run()
    except KeyboardInterrupt:
        logger.log_info("KeyboardInterrupt received. Shutting down gracefully...")
        shutdown_event.set()
        time.sleep(2) # Allow threads to flush
        logger.log_info("Shutdown complete.")
        sys.exit(0)