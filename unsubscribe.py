import os
import csv
from datetime import datetime, timedelta
from flask import Flask, request, render_template_string
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from threading import Thread
import time

# SMTP Configuration
REPORT_EMAIL = "b2bgrowthexpo@gmail.com"
SMTP_SERVER = "mail.miltonkeynesexpo.com"
SMTP_PORT = 587
SENDER_EMAIL = "mike@miltonkeynesexpo.com"
SENDER_PASSWORD = "dvnn-&-((jdK"
CSV_FILE = "unsubscribes.csv"
ATTACHMENT_FILE = "unsubscribed_emails_report.csv"

# Ensure CSV exists
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["email", "timestamp"])

# Flask setup
app = Flask(__name__)

@app.route("/unsubscribe")
def unsubscribe():
    email = request.args.get("email")
    if not email:
        return "No email provided", 400

    # Save to CSV
    with open(CSV_FILE, "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([email, datetime.utcnow().isoformat()])

    # Show user-friendly message
    return render_template_string(f"""
        <html>
        <head><title>Unsubscribed</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h2 style="color: #E74C3C;">You’ve been unsubscribed</h2>
            <p style="font-size: 18px;">We're sorry to see you go, <strong>{email}</strong>.</p>
            <p style="color: #555;">You will no longer receive emails from us.</p>
        </body>
        </html>
    """)

# Email report function (with CSV attachment)
def send_unsubscribe_report():
    since = datetime.utcnow() - timedelta(days=1)
    unsubscribed = []

    with open(CSV_FILE, "r") as file:
        reader = csv.reader(file)
        next(reader)  # Skip header
        for row in reader:
            if len(row) != 2:
                continue
            email, timestamp = row
            try:
                if datetime.fromisoformat(timestamp) > since:
                    unsubscribed.append((email, timestamp))
            except:
                continue

    if not unsubscribed:
        print("No unsubscribes in the last 24 hours.")
        return

    # Create a temporary CSV file for the report
    with open(ATTACHMENT_FILE, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["email", "timestamp"])
        writer.writerows(unsubscribed)

    # Email body text
    body = "Here is the unsubscribe report for the last 24 hours. The attached CSV contains the unsubscribed emails."

    # Create a multipart email message
    msg = MIMEMultipart()
    msg["Subject"] = "Daily Unsubscribe Report"
    msg["From"] = SENDER_EMAIL
    msg["To"] = REPORT_EMAIL
    msg.attach(MIMEText(body, "plain"))

    # Attach the CSV file
    with open(ATTACHMENT_FILE, "rb") as attachment:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={ATTACHMENT_FILE}")
        msg.attach(part)

    # Send the email
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, REPORT_EMAIL, msg.as_string())
        print("✅ Unsubscribe report with attachment sent.")
    except Exception as e:
        print(f"❌ Failed to send report: {e}")

    # Remove the temporary CSV file
    try:
        os.remove(ATTACHMENT_FILE)
    except FileNotFoundError:
        print(f"❌ Attachment file not found: {ATTACHMENT_FILE}")

# Background thread to run daily at 9:00 AM IST
def start_daily_report_thread():
    def loop():
        IST_OFFSET = timedelta(hours=5, minutes=30)  # IST is UTC+5:30
        while True:
            now_utc = datetime.utcnow()
            now_ist = now_utc + IST_OFFSET
            next_run_ist = now_ist.replace(hour=9, minute=0, second=0, microsecond=0)

            if now_ist >= next_run_ist:
                next_run_ist += timedelta(days=1)

            sleep_seconds = (next_run_ist - now_ist).total_seconds()
            print(f"⏰ Next unsubscribe report scheduled in {int(sleep_seconds)} seconds (9:00 AM IST)")
            time.sleep(sleep_seconds)
            send_unsubscribe_report()
    Thread(target=loop, daemon=True).start()

# Start thread for the 24-hour interval report
start_daily_report_thread()

# Route to manually trigger the unsubscribe report
@app.route('/send_report')
def send_report():
    send_unsubscribe_report()
    return "Unsubscribe report has been sent!"

# Start Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
