import os
import sys
import io
import logging
import asyncio
import smtplib
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import RPCError

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

SENDER_EMAIL = "soham.techanalogy@gmail.com"
RECIPIENT_EMAIL = "lisakinny12@gmail.com"
TARGET_CHANNEL = "Indian_Express_Newspaper_p"
SMTP_SERVER = "smtp.gmail.com"

PERSONALIZED_QUOTES = [
    "Go get the day, my stunning lady! You've got this.",
    "Good morning gorgeous! Go out there and shine bright today.",
    "Believe in yourself today as much as I believe in you every single second.",
    "Remember today how brilliant, strong, and deeply loved you are.",
    "Go conquer the world today, my stunning girl!",
    "Start your day with a smile and know that I'm always cheering for you.",
    "Whatever you tackle today, you're going to crush it. Go get 'em, my lady!",
    "Wake up and be awesome! Wishing you an extraordinary day ahead."
]

def get_ist_date() -> str:
    """Calculate current date in DD-MM-YYYY format adjusted for IST (UTC+5:30)."""
    ist = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    return ist.strftime("%d-%m-%Y")

def get_daily_quote() -> str:
    """Return a dynamic personalized quote based on the current day of the year."""
    ist_now = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    day_of_year = ist_now.timetuple().tm_yday
    return PERSONALIZED_QUOTES[day_of_year % len(PERSONALIZED_QUOTES)]

def send_email(pdf_bytes: bytes, filename: str, date_str: str, app_password: str) -> bool:
    """Construct EmailMessage payload directly from in-memory buffer and send via SMTP over Gmail."""
    logging.info(f"Preparing email payload ({len(pdf_bytes)} bytes) for recipient {RECIPIENT_EMAIL}...")
    try:
        quote = get_daily_quote()
        msg = EmailMessage()
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECIPIENT_EMAIL
        msg["Subject"] = f"Indian Express Mumbai - [{date_str}]"
        
        email_body = f"""Good morning, my stunning lady! ❤️

Here is today's Indian Express newspaper for you ({date_str}).

✨ Thought of the Day:
"{quote}"

Go get the day!
"""
        msg.set_content(email_body)

        msg.add_attachment(
            pdf_bytes,
            maintype="application",
            subtype="pdf",
            filename=filename
        )

        logging.info(f"Connecting to SMTP server {SMTP_SERVER}:587...")
        with smtplib.SMTP(SMTP_SERVER, 587, timeout=180) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SENDER_EMAIL, app_password)
            server.send_message(msg)
            logging.info("Email payload transmitted successfully.")
            return True
    except smtplib.SMTPAuthenticationError:
        logging.error("SMTP Authentication Failed. Check APP_PASSWORD and SENDER_EMAIL credentials.")
        return False
    except smtplib.SMTPException as e:
        logging.error(f"SMTP protocol error occurred: {e}")
        return False
    except Exception as e:
        logging.error(f"Failed to transmit email: {e}")
        return False

async def run_pipeline(api_id: int, api_hash: str, session_str: str, app_password: str):
    date_str = get_ist_date()
    sent_tag = f"SENT: IE Mumbai {date_str}"
    target_filenames = [
        f"IE Mumbai [{date_str}].pdf",
        f"IE Mumbai {date_str}.pdf"
    ]

    logging.info(f"Connecting to Telegram (Date: {date_str})...")
    try:
        async with TelegramClient(StringSession(session_str), api_id, api_hash) as client:
            # 1. State Check: Check if today's paper was already delivered
            already_sent = False
            async for msg in client.iter_messages('me', limit=15):
                if msg.text and sent_tag in msg.text:
                    already_sent = True
                    break

            if already_sent:
                logging.info(f"Today's edition ({date_str}) was ALREADY delivered successfully. Skipping attempt.")
                return

            # 2. Search target paper in channel
            logging.info(f"Searching channel '{TARGET_CHANNEL}' for {target_filenames}...")
            target_msg = None
            async for message in client.iter_messages(TARGET_CHANNEL, limit=20):
                if message.file and message.file.name in target_filenames:
                    target_msg = message
                    break

            if not target_msg:
                logging.info(f"Paper for date {date_str} is not published on Telegram yet. Will retry on next scheduled fallback.")
                return

            # 3. Direct In-Memory Download (Zero Disk I/O)
            logging.info("Target file found. Streaming into memory buffer...")
            pdf_buffer = io.BytesIO()
            await target_msg.download_media(file=pdf_buffer)
            pdf_bytes = pdf_buffer.getvalue()
            
            if not pdf_bytes or len(pdf_bytes) == 0:
                logging.error("Download completed but memory buffer is empty.")
                sys.exit(1)

            logging.info(f"Memory stream complete ({len(pdf_bytes)} bytes).")

            # 4. Transmit Email Payload
            attachment_name = target_msg.file.name or f"IE Mumbai [{date_str}].pdf"
            email_sent = send_email(pdf_bytes, attachment_name, date_str, app_password)
            
            if email_sent:
                # 5. Record State Tag in Telegram Saved Messages ('me')
                ist_time_str = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime('%H:%M:%S')
                await client.send_message('me', f"{sent_tag} at {ist_time_str}")
                logging.info(f"State recorded in Saved Messages: '{sent_tag}'")
            else:
                logging.error("Email delivery failed.")
                sys.exit(1)

    except RPCError as e:
        logging.error(f"Telegram RPC Error during execution: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error in pipeline: {e}")
        sys.exit(1)

def main():
    api_id_env = os.environ.get("API_ID")
    api_hash = os.environ.get("API_HASH")
    session_string = os.environ.get("SESSION_STRING")
    app_password = os.environ.get("APP_PASSWORD")

    missing_vars = []
    if not api_id_env: missing_vars.append("API_ID")
    if not api_hash: missing_vars.append("API_HASH")
    if not session_string: missing_vars.append("SESSION_STRING")
    if not app_password: missing_vars.append("APP_PASSWORD")

    if missing_vars:
        logging.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)

    try:
        api_id = int(api_id_env)
    except ValueError:
        logging.error("Environment variable API_ID must be a valid integer.")
        sys.exit(1)

    asyncio.run(run_pipeline(api_id, api_hash, session_string, app_password))

if __name__ == "__main__":
    main()
