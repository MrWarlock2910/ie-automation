import os
import sys
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
SMTP_PORT = 465

def get_ist_date() -> str:
    """Calculate current date in DD-MM-YYYY format adjusted for IST (UTC+5:30)."""
    ist = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    return ist.strftime("%d-%m-%Y")

async def download_target_pdf(api_id: int, api_hash: str, session_str: str, date_str: str, output_path: str) -> bool:
    """Authenticate TelegramClient using StringSession, search recent messages, and download target file."""
    target_filenames = [
        f"IE Mumbai [{date_str}].pdf",
        f"IE Mumbai {date_str}.pdf"
    ]
    logging.info(f"Connecting to Telegram to locate file for date: {date_str}")
    try:
        async with TelegramClient(StringSession(session_str), api_id, api_hash) as client:
            target_msg = None
            async for message in client.iter_messages(TARGET_CHANNEL, limit=20):
                if message.file and message.file.name in target_filenames:
                    target_msg = message
                    break

            if not target_msg:
                logging.error(f"Target file matching {target_filenames} not found in recent 20 messages of channel '{TARGET_CHANNEL}'.")
                return False

            logging.info(f"Target file found. Downloading to {output_path}...")
            await target_msg.download_media(file=output_path)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logging.info(f"File successfully downloaded: {output_path} ({os.path.getsize(output_path)} bytes)")
                return True
            else:
                logging.error("Download completed but destination file is missing or empty.")
                return False
    except RPCError as e:
        logging.error(f"Telegram RPC Error during execution: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error while downloading Telegram media: {e}")
        return False

PERSONALIZED_QUOTES = [
    "Go get the day, my stunning lady! You've got this, and I'm always cheering for you.",
    "Good morning, my love! Shine bright today and conquer everything with your amazing smile.",
    "Wake up and be awesome! Wishing the most beautiful woman an extraordinary day ahead.",
    "Remember today how brilliant, strong, and deeply cherished you are. Go get 'em, my lady!",
    "Another day, another opportunity for you to do great things. Keep inspiring, my stunning partner!",
    "Good morning gorgeous! May your day be as radiant and wonderful as you are to me.",
    "Believe in yourself today as much as I believe in you every single second. Have a fabulous day!",
    "Sending you a warm hug, positive energy, and all my love to start your morning. Go rule the day!"
]

def get_daily_quote() -> str:
    """Return a dynamic personalized quote based on the current day of the year."""
    ist_now = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    day_of_year = ist_now.timetuple().tm_yday
    return PERSONALIZED_QUOTES[day_of_year % len(PERSONALIZED_QUOTES)]

def send_email(pdf_path: str, date_str: str, app_password: str) -> bool:
    """Construct EmailMessage payload and send via SMTP over Gmail."""
    logging.info(f"Preparing email payload for recipient {RECIPIENT_EMAIL}...")
    try:
        quote = get_daily_quote()
        msg = EmailMessage()
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECIPIENT_EMAIL
        msg["Subject"] = f"Indian Express Mumbai - [{date_str}]"
        
        email_body = f"""Good morning, my stunning lady! ❤️

Here is your Indian Express newspaper for {date_str}.

✨ Thought of the Day ✨
"{quote}"

Go get the day and have an incredible morning!
"""
        msg.set_content(email_body)

        with open(pdf_path, "rb") as f:
            file_data = f.read()
            file_name = os.path.basename(pdf_path)

        msg.add_attachment(
            file_data,
            maintype="application",
            subtype="pdf",
            filename=file_name
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

def cleanup_tmp_file(file_path: str) -> None:
    """Safely remove downloaded file from temporary storage."""
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            logging.info(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logging.error(f"Error cleaning up file {file_path}: {e}")

async def main():
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

    date_str = get_ist_date()
    target_filename = f"IE Mumbai [{date_str}].pdf"
    
    tmp_dir = "/tmp" if os.path.exists("/tmp") else os.getenv("TEMP", "/tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    pdf_path = os.path.join(tmp_dir, target_filename)

    try:
        success = await download_target_pdf(api_id, api_hash, session_string, date_str, pdf_path)
        if success:
            email_sent = send_email(pdf_path, date_str, app_password)
            if not email_sent:
                logging.error("Email transmission failed.")
                sys.exit(1)
        else:
            logging.error("Execution halted due to media download failure.")
            sys.exit(1)
    finally:
        cleanup_tmp_file(pdf_path)

if __name__ == "__main__":
    asyncio.run(main())
