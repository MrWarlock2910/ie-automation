import os
import sys
import logging
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TARGET_CHANNEL = "Indian_Express_Newspaper_p"

async def inspect():
    api_id = int(os.environ["API_ID"])
    api_hash = os.environ["API_HASH"]
    session_str = os.environ["SESSION_STRING"]

    async with TelegramClient(StringSession(session_str), api_id, api_hash) as client:
        logging.info(f"Connected. Fetching last 60 messages from {TARGET_CHANNEL}...")
        count = 0
        async for msg in client.iter_messages(TARGET_CHANNEL, limit=60):
            count += 1
            file_name = msg.file.name if msg.file else None
            file_size = msg.file.size if msg.file else None
            date_time = msg.date.strftime("%Y-%m-%d %H:%M:%S UTC")
            text_snippet = (msg.text or "").replace("\n", " ")[:60]
            print(f"[{count:02d}] Date: {date_time} | File: {file_name} ({file_size} bytes) | Text: {text_snippet}")

if __name__ == "__main__":
    asyncio.run(inspect())
