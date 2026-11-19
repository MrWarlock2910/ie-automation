import os
import sys
import logging
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def list_dialogs():
    api_id = int(os.environ["API_ID"])
    api_hash = os.environ["API_HASH"]
    session_str = os.environ["SESSION_STRING"]

    async with TelegramClient(StringSession(session_str), api_id, api_hash) as client:
        logging.info("Connected to Telegram. Fetching dialogs...")
        dialogs = await client.get_dialogs(limit=100)
        print(f"Total dialogs found: {len(dialogs)}")
        for d in dialogs:
            entity_type = type(d.entity).__name__
            safe_title = ascii(d.title)
            print(f"ID: {d.id} | Title: {safe_title} | Username: {getattr(d.entity, 'username', None)} | Type: {entity_type}")

if __name__ == "__main__":
    asyncio.run(list_dialogs())
