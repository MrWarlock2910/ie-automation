import os
import sys
import logging
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def generate_session():
    api_id = os.environ.get("API_ID") or input("Enter API_ID: ").strip()
    api_hash = os.environ.get("API_HASH") or input("Enter API_HASH: ").strip()

    if not api_id or not api_hash:
        logging.error("API_ID and API_HASH are required.")
        sys.exit(1)

    try:
        api_id = int(api_id)
    except ValueError:
        logging.error("API_ID must be a valid integer.")
        sys.exit(1)

    logging.info("Initializing Telegram client...")
    try:
        with TelegramClient(StringSession(), api_id, api_hash) as client:
            session_str = client.session.save()
            print("\n" + "=" * 60)
            print("YOUR TELETHON STRING SESSION TOKEN:")
            print(session_str)
            print("=" * 60 + "\n")
            logging.info("Session string successfully generated!")
    except Exception as e:
        logging.error(f"Failed to generate StringSession: {e}")
        sys.exit(1)

if __name__ == "__main__":
    generate_session()
