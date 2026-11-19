import os
import sys
import logging
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

NEW_CHANNEL_ID = -1003991569979

async def inspect_new_channel():
    api_id = int(os.environ["API_ID"])
    api_hash = os.environ["API_HASH"]
    session_str = os.environ["SESSION_STRING"]

    async with TelegramClient(StringSession(session_str), api_id, api_hash) as client:
        logging.info(f"Connected to Telegram. Fetching entity for {NEW_CHANNEL_ID}...")
        entity = await client.get_entity(NEW_CHANNEL_ID)
        logging.info(f"Target Channel Entity: {entity.title} (ID: {entity.id})")
        
        count = 0
        print("\n=== RECENT MESSAGES IN PRIVATE NEWS CHANNEL ===")
        async for msg in client.iter_messages(entity, limit=50):
            count += 1
            file_name = msg.file.name if msg.file else None
            file_size = msg.file.size if msg.file else None
            date_time = msg.date.strftime("%Y-%m-%d %H:%M:%S UTC")
            text = (msg.text or "").replace("\n", " ")[:80]
            print(f"[{count:02d}] Date: {date_time} | File: {ascii(file_name)} ({file_size} B) | Text: {ascii(text)}")

if __name__ == "__main__":
    asyncio.run(inspect_new_channel())
