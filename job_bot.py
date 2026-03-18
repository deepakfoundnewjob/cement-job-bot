import os
import imaplib
import email
import sqlite3
import requests
import schedule
import time
from dotenv import load_dotenv

load_dotenv()

# Telegram
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Gmail
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")

print("🚀 Multi-Portal Job Bot Starting...")
print("📧 Email:", EMAIL_ADDRESS)

# Database
conn = sqlite3.connect("jobs.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS jobs (link TEXT PRIMARY KEY)")
conn.commit()

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=data)

def is_duplicate(link):
    cursor.execute("SELECT link FROM jobs WHERE link=?", (link,))
    return cursor.fetchone() is not None

def save_job(link):
    cursor.execute("INSERT INTO jobs (link) VALUES (?)", (link,))
    conn.commit()

def check_email():
    print("🔎 Checking Gmail for job alerts...")

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    mail.select("inbox")

    # Read ALL unread job emails
    status, messages = mail.search(None, '(UNSEEN)')

    if status != "OK":
        print("No unread emails.")
        return

    for num in messages[0].split():
        status, data = mail.fetch(num, "(RFC822)")
        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)

        subject = msg["subject"] or ""
        print("📩 Email Subject:", subject)

        body = ""

        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body += part.get_payload(decode=True).decode(errors="ignore")
        else:
            body = msg.get_payload(decode=True).decode(errors="ignore")

        full_text = (subject + " " + body).lower()

        # Industry filter
        industry_keywords = ["cement", "building material", "concrete", "rmc"]

        # Leadership filter
        role_keywords = [
            "sales head",
            "regional sales",
            "state head",
            "business head",
            "cluster head",
            "zonal head",
            "technical head",
            "sales manager"
        ]

        if any(ind in full_text for ind in industry_keywords) and \
           any(role in full_text for role in role_keywords):

            # Extract links
            for word in body.split():
                if "http" in word:
                    clean_link = word.strip()

                    if not is_duplicate(clean_link):
                        message = f"🚨 Cement Leadership Job Alert\n\n📌 {subject}\n🔗 {clean_link}"
                        send_telegram(message)
                        save_job(clean_link)

    mail.logout()

schedule.every(5).minutes.do(check_email)

send_telegram("✅ Multi-Portal Email Job Bot Activated")

check_email()

while True:
    schedule.run_pending()
    time.sleep(1)