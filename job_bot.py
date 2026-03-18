import os
import imaplib
import email
import sqlite3
import requests
import schedule
import time
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")

print("🚀 Executive Company Tracking Bot Starting...")
print("📧 Email:", EMAIL_ADDRESS)

conn = sqlite3.connect("jobs.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS jobs (link TEXT PRIMARY KEY)")
conn.commit()

collected_jobs = []

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
    global collected_jobs

    print("🔎 Checking Gmail for target companies...")

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    mail.select("inbox")

    status, messages = mail.search(None, '(UNSEEN)')

    if status != "OK":
        return

    for num in messages[0].split():
        status, data = mail.fetch(num, "(RFC822)")
        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)

        subject = msg["subject"] or ""
        body = ""

        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body += part.get_payload(decode=True).decode(errors="ignore")
        else:
            body = msg.get_payload(decode=True).decode(errors="ignore")

        full_text = (subject + " " + body).lower()

        # Industry Keywords
        industry_keywords = [
            "cement", "concrete", "rmc", "steel",
            "building material", "construction chemical",
            "tiles", "sanitary", "paint"
        ]

        # Leadership Keywords
        leadership_keywords = [
            "sales head", "regional sales", "state head",
            "zonal head", "cluster head", "business head",
            "vp sales", "vice president", "gm sales",
            "general manager", "director sales",
            "technical head"
        ]

        # Target Companies
        company_keywords = [
            "ultratech",
            "shree cement",
            "dalmia",
            "ambuja",
            "acc",
            "jsw",
            "tata steel",
            "kajaria",
            "somany",
            "cera",
            "hindware",
            "asian paints",
            "berger",
            "nerolac"
        ]

        if (any(ind in full_text for ind in industry_keywords) and
            any(role in full_text for role in leadership_keywords) and
            any(comp in full_text for comp in company_keywords)):

            for word in body.split():
                if "http" in word:
                    clean_link = word.strip()

                    if not is_duplicate(clean_link):
                        collected_jobs.append((subject, clean_link))
                        save_job(clean_link)

    mail.logout()

def send_hourly_report():
    global collected_jobs

    print("📊 Sending hourly executive company report...")

    if collected_jobs:
        message = "📊 Target Company Leadership Report (Last 1 Hour)\n\n"
        for i, (title, link) in enumerate(collected_jobs, 1):
            message += f"{i}️⃣ {title}\n🔗 {link}\n\n"
    else:
        message = "📊 Target Company Leadership Report (Last 1 Hour)\n\nNo new relevant roles from tracked companies."

    send_telegram(message)
    collected_jobs = []

schedule.every(5).minutes.do(check_email)
schedule.every(1).hours.do(send_hourly_report)

send_telegram("✅ Executive Company Tracking Bot Activated")

while True:
    schedule.run_pending()
    time.sleep(1)