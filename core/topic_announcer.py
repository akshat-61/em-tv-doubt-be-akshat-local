import json
import time
import threading

def _parse_time(ts):
    parts = list(map(int, ts.split(":")))
    if len(parts) == 2:
        m, s = parts
        return m * 60 + s
    h, m, s = parts
    return h * 3600 + m * 60 + s


def start_announcer(stream_start_epoch, send_message, yt, chat_id):
    def worker():
        print("Topic Announcer Started")

        try:
            with open("data/topics.json", "r", encoding="utf-8") as f:
                topics = json.load(f)
        except Exception as e:
            print(f"[Announcer Error] {e}")
            return

        for t in topics:
            t["seconds"] = _parse_time(t["at"])
            t["sent"] = False

        while True:
            elapsed = time.time() - stream_start_epoch

            for topic in topics:
                if not topic["sent"] and elapsed >= topic["seconds"]:
                    msg = f"📌 [{topic['at']}] {topic['title']}\n{topic['message']}"

                    try:
                        send_message(yt, chat_id, msg)
                        print(f"[ANNOUNCED] {msg}")
                        topic["sent"] = True
                    except Exception as e:
                        print(f"[Announcer Send Error] {e}")

            time.sleep(5)

    threading.Thread(target=worker, daemon=True).start()