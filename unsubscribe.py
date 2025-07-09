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
REPORT_EMAILS = ["b2bgrowthexpo@gmail.com", "miltonkeynesexpo@gmail.com"]
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

@app.route("/")
def home():
    return "✅ Unsubscribe server is running.", 200

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

def send_unsubscribe_report():
    since = datetime.utcnow() - timedelta(hours=12)
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
        print("📭 No unsubscribes in the last 12 hours.")
        return

    # Create report file
    with open(ATTACHMENT_FILE, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["email", "timestamp"])
        writer.writerows(unsubscribed)

    # Email body text
    body = "Here is the unsubscribe report for the last 12 hours. The attached CSV contains the unsubscribed emails."

    # Email setup
    msg = MIMEMultipart()
    msg["Subject"] = "Unsubscribe Report - Last 12 Hours"
    msg["From"] = SENDER_EMAIL
    msg["To"] = ", ".join(REPORT_EMAILS)
    msg.attach(MIMEText(body, "plain"))

    with open(ATTACHMENT_FILE, "rb") as attachment:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={ATTACHMENT_FILE}")
        msg.attach(part)

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, REPORT_EMAILS, msg.as_string())
        print("📧 Unsubscribe report sent with attachment.")
    except Exception as e:
        print(f"❌ Failed to send report: {e}")

    try:
        os.remove(ATTACHMENT_FILE)
    except FileNotFoundError:
        print(f"❌ Attachment file not found: {ATTACHMENT_FILE}")

# Run the report every 12 hours
def start_12hr_report_thread():
    def loop():
        while True:
            print("⏳ Waiting 12 hours for next report...")
            time.sleep(12 * 60 * 60)  # 12 hours
            send_unsubscribe_report()
    Thread(target=loop, daemon=True).start()

# Start the reporting thread
start_12hr_report_thread()

# Manual trigger
@app.route('/send_report')
def send_report():
    send_unsubscribe_report()
    return "Unsubscribe report has been sent!"

# Start Flask app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
