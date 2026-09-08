import os
import sys
import io
import time
import logging
import asyncio
import smtplib
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import RPCError, FloodWaitError

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

SENDER_EMAIL = "soham.techanalogy@gmail.com"
RECIPIENT_EMAIL = "lisakinny12@gmail.com"
TARGET_CHANNEL = "Indian_Express_Newspaper_p"
SMTP_SERVER = "smtp.gmail.com"

# Poll interval in seconds while actively watching for the morning paper
POLL_INTERVAL_SECONDS = 45
# Maximum time (in minutes) the watcher will run per heartbeat before exiting cleanly
MAX_WATCH_DURATION_MINUTES = 2
SENTINEL_FILE = ".delivery_marker"

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

def get_ist_now() -> datetime:
    """Return current datetime in IST (UTC+5:30)."""
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))

def get_ist_date() -> str:
    """Calculate current date in DD-MM-YYYY format adjusted for IST (UTC+5:30)."""
    return get_ist_now().strftime("%d-%m-%Y")

def get_daily_quote() -> str:
    """Return a dynamic personalized quote based on the current day of the year."""
    day_of_year = get_ist_now().timetuple().tm_yday
    return PERSONALIZED_QUOTES[day_of_year % len(PERSONALIZED_QUOTES)]

def mark_delivered(date_str: str):
    """Write local sentinel file to indicate successful delivery for the given date."""
    try:
        with open(SENTINEL_FILE, "w", encoding="utf-8") as f:
            f.write(f"delivered:{date_str}\n")
        logging.info(f"Sentinel file '{SENTINEL_FILE}' created for {date_str}.")
    except Exception as e:
        logging.warning(f"Failed to create sentinel file: {e}")

def is_already_delivered_locally(date_str: str) -> bool:
    """Check if local sentinel file confirms today's paper was delivered."""
    if os.path.exists(SENTINEL_FILE):
        try:
            with open(SENTINEL_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if f"delivered:{date_str}" in content:
                    return True
        except Exception:
            return False
    return False

def is_target_newspaper(filename: str, date_str: str) -> bool:
    """Robust, casing- and delimiter-agnostic filename matcher for Mumbai editions."""
    if not filename or not filename.lower().endswith(".pdf"):
        return False
    cleaned = (
        filename.lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("[", "")
        .replace("]", "")
        .replace("(", "")
        .replace(")", "")
        .replace("-", "")
        .replace(".", "")
    )
    date_digits = date_str.replace("-", "").replace(".", "").replace("/", "")
    is_mumbai = "iemumbai" in cleaned or "indianexpressmumbai" in cleaned or ("express" in cleaned and "mumbai" in cleaned)
    return is_mumbai and date_digits in cleaned

def send_email(pdf_bytes: bytes, filename: str, date_str: str, app_password: str) -> bool:
    """Construct EmailMessage payload directly from in-memory buffer and send via SMTP over Gmail with retries."""
    logging.info(f"Preparing email payload ({len(pdf_bytes)} bytes) for recipient {RECIPIENT_EMAIL}...")
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

    MAX_SMTP_RETRIES = 3
    for attempt in range(1, MAX_SMTP_RETRIES + 1):
        try:
            logging.info(f"[Attempt {attempt}/{MAX_SMTP_RETRIES}] Connecting to SMTP server {SMTP_SERVER}:587...")
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
        except (smtplib.SMTPException, OSError) as e:
            logging.warning(f"SMTP error on attempt {attempt}/{MAX_SMTP_RETRIES}: {e}")
            if attempt < MAX_SMTP_RETRIES:
                time.sleep(5)
            else:
                logging.error(f"All {MAX_SMTP_RETRIES} SMTP transmission attempts failed.")
                return False
        except Exception as e:
            logging.error(f"Unexpected error transmitting email: {e}")
            return False
    return False

async def run_pipeline(api_id: int, api_hash: str, session_str: str, app_password: str):
    current_ist = get_ist_now()
    hour = current_ist.hour
    minute = current_ist.minute

    # 1. Active Window Guard: Only run between 07:30 AM and 07:00 PM IST
    is_active = (hour == 7 and minute >= 30) or (8 <= hour < 19)
    if not is_active:
        logging.info(f"Current time ({current_ist.strftime('%H:%M:%S IST')}) is outside active hours (07:30 - 19:00 IST). Skipping.")
        return

    date_str = get_ist_date()
    sent_tag = f"SENT: IE Mumbai {date_str}"

    # 2. Local Sentinel Check (Zero network round-trip)
    if is_already_delivered_locally(date_str):
        logging.info(f"Today's edition ({date_str}) already recorded delivered locally. Skipping pipeline.")
        return

    start_time = get_ist_now()
    logging.info(f"Starting Heartbeat Check (Date: {date_str}, Time: {start_time.strftime('%H:%M:%S IST')})...")

    MAX_FLOOD_RETRIES = 2
    for flood_attempt in range(MAX_FLOOD_RETRIES + 1):
        try:
            async with TelegramClient(
                StringSession(session_str),
                api_id,
                api_hash,
                flood_sleep_threshold=300
            ) as client:
                # 3. Deduplication check via Telegram Saved Messages
                already_sent = False
                async for msg in client.iter_messages('me', limit=15):
                    if msg.text and sent_tag in msg.text:
                        already_sent = True
                        break

                if already_sent:
                    logging.info(f"Today's edition ({date_str}) was ALREADY delivered. Recording local sentinel and skipping heartbeat.")
                    mark_delivered(date_str)
                    return

                # 4. Active Heartbeat Scan Loop
                attempt_count = 0
                while True:
                    attempt_count += 1
                    current_time = get_ist_now()
                    elapsed_minutes = (current_time - start_time).total_seconds() / 60

                    if elapsed_minutes >= MAX_WATCH_DURATION_MINUTES:
                        logging.info(f"Heartbeat scan limit ({MAX_WATCH_DURATION_MINUTES}m) reached without new upload. Exiting until next heartbeat.")
                        break

                    logging.info(f"[Check #{attempt_count}] Scanning '{TARGET_CHANNEL}' for Mumbai edition ({date_str})...")
                    target_msg = None
                    async for message in client.iter_messages(TARGET_CHANNEL, limit=25):
                        if message.file and is_target_newspaper(message.file.name, date_str):
                            target_msg = message
                            break

                    if target_msg:
                        logging.info(f"[MATCH FOUND] Target file: '{target_msg.file.name}'. Streaming into memory...")
                        pdf_buffer = io.BytesIO()
                        await target_msg.download_media(file=pdf_buffer)
                        pdf_bytes = pdf_buffer.getvalue()

                        if not pdf_bytes or len(pdf_bytes) == 0:
                            logging.error("Download completed but memory buffer is empty.")
                            sys.exit(1)

                        logging.info(f"Memory download complete ({len(pdf_bytes)} bytes). Transmitting email...")
                        attachment_name = target_msg.file.name or f"IE Mumbai [{date_str}].pdf"
                        email_sent = send_email(pdf_bytes, attachment_name, date_str, app_password)

                        if email_sent:
                            delivered_time = get_ist_now().strftime('%H:%M:%S IST')
                            await client.send_message('me', f"{sent_tag} at {delivered_time}")
                            mark_delivered(date_str)
                            logging.info(f"[COMPLETED] State recorded in Saved Messages & Sentinel: '{sent_tag} at {delivered_time}'. Done!")
                            return
                        else:
                            logging.error("Email delivery failed after multiple retries.")
                            sys.exit(1)

                    logging.info(f"Paper for {date_str} not published yet. Next check in {POLL_INTERVAL_SECONDS}s.")
                    await asyncio.sleep(POLL_INTERVAL_SECONDS)
            
            # Finished scan loop cleanly without matches
            return

        except FloodWaitError as e:
            logging.warning(f"Telegram FloodWaitError encountered: {e.seconds}s required.")
            if e.seconds <= 450 and flood_attempt < MAX_FLOOD_RETRIES:
                wait_time = e.seconds + 2
                logging.info(f"Sleeping for {wait_time}s to clear FloodWait before retry #{flood_attempt + 1}...")
                await asyncio.sleep(wait_time)
            else:
                logging.warning(f"Telegram FloodWait ({e.seconds}s) exceeds in-run threshold or retries exhausted. Exiting cleanly (exit 0) until next scheduled heartbeat.")
                return

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
