import sys
import config
from chat_handler import run, shutdown_event
import os
import time
from topic_parser import parse_text_to_json
import logger

if __name__ == "__main__":
    if os.path.exists("topics.txt"):
        parse_text_to_json("topics.txt")

    try:
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