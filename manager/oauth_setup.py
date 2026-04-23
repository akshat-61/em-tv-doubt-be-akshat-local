import os
from google_auth_oauthlib.flow import InstalledAppFlow
from util.config import YOUTUBE_CLIENT_SECRET_FILE

SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

TOKEN_FILE = "token.json"


def main():
    if not os.path.exists(YOUTUBE_CLIENT_SECRET_FILE):
        print(f"[ERROR] Client secret file not found: {YOUTUBE_CLIENT_SECRET_FILE}")
        print("Download it from Google Cloud Console → APIs & Services → Credentials")
        return

    print("[OAuth] Opening browser for YouTube authorisation...")
    flow = InstalledAppFlow.from_client_secrets_file(
        YOUTUBE_CLIENT_SECRET_FILE, SCOPES
    )
    credentials = flow.run_local_server(port=0)

    with open(TOKEN_FILE, "w") as f:
        f.write(credentials.to_json())

    print(f"[OAuth] Token saved to {TOKEN_FILE}")
    print("[OAuth] You can now run main.py — the bot will use this token to send replies.")


if __name__ == "__main__":
    main()
