import os
import csv
from datetime import datetime, timedelta
from flask import Flask, request, render_template_string, jsonify
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from threading import Thread
import time
import urllib.parse
import re

# ===================== SMTP Configuration =====================
REPORT_EMAILS = ["b2bgrowthexpo@gmail.com", "miltonkeynesexpo@gmail.com"]
SMTP_SERVER = "mail.miltonkeynesexpo.com"
SMTP_PORT = 587
SENDER_EMAIL = "mike@miltonkeynesexpo.com"
SENDER_PASSWORD = "dvnn-&-((jdK"
CSV_FILE = "unsubscribes.csv"
ATTACHMENT_FILE = "unsubscribed_emails_report.csv"

# ===================== Ensure CSV Exists =====================
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["email", "timestamp"])

# ===================== Flask App Setup =====================
app = Flask(__name__)

EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# --------------------- Helper Functions ---------------------
def clean_email(raw_email: str) -> str | None:
    """Decode and validate email address."""
    if not raw_email:
        return None
    email = urllib.parse.unquote_plus(raw_email).strip().lower()
    if EMAIL_PATTERN.match(email):
        return email
    return None

def read_unsubscribes():
    with open(CSV_FILE, newline="") as f:
        reader = csv.reader(f)
        next(reader, None)
        return [row for row in reader if len(row) == 2]

def write_unsubscribes(rows):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["email", "timestamp"])
        writer.writerows(rows)

# --------------------- Flask Routes ---------------------
@app.route("/")
def home():
    return "✅ Unsubscribe server running.", 200

@app.route("/unsubscribe")
def unsubscribe():
    raw_email = request.args.get("email")
    email = clean_email(raw_email)

    if not email:
        return render_template_string("""
        <html><body style="font-family:Arial;text-align:center;padding:50px;">
        <h2 style="color:#E74C3C;">Invalid Unsubscribe Request</h2>
        <p>We could not process your request because the email address was invalid.</p>
        </body></html>
        """), 400

    # avoid duplicates
    existing = read_unsubscribes()
    if any(row[0] == email for row in existing):
        return render_template_string(f"""
        <html><body style="font-family:Arial;text-align:center;padding:50px;">
        <h2 style="color:#3498DB;">Already Unsubscribed</h2>
        <p><strong>{email}</strong> is already unsubscribed.</p>
        </body></html>
        """)

    # save new unsubscribe
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([email, datetime.utcnow().isoformat()])

    return render_template_string(f"""
        <html><head><title>Unsubscribed</title></head>
        <body style="font-family: Arial; text-align:center; padding:50px;">
            <h2 style="color:#E74C3C;">You’ve been unsubscribed</h2>
            <p style="font-size:18px;">We're sorry to see you go, <strong>{email}</strong>.</p>
            <p style="color:#555;">You will no longer receive our emails.</p>
        </body></html>
    """)

@app.route("/get_unsubscribes")
def get_unsubscribes():
    """API endpoint for campaign script to pull unsubscribed emails."""
    unsubscribes = [row[0] for row in read_unsubscribes()]
    return jsonify({"unsubscribed": unsubscribes, "count": len(unsubscribes)})

# --------------------- Reporting & Cleanup ---------------------
def send_unsubscribe_report():
    since = datetime.utcnow() - timedelta(hours=12)
    unsubscribed = [r for r in read_unsubscribes()
                    if datetime.fromisoformat(r[1]) > since]

    if not unsubscribed:
        print("📭 No unsubscribes in the last 12 hours.")
        return

    # Write report file
    with open(ATTACHMENT_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["email", "timestamp"])
        writer.writerows(unsubscribed)

    # Build email
    msg = MIMEMultipart()
    msg["Subject"] = "Unsubscribe Report - Last 12 Hours"
    msg["From"] = SENDER_EMAIL
    msg["To"] = ", ".join(REPORT_EMAILS)
    body = ("Here is the unsubscribe report for the last 12 hours.\n"
            "The attached CSV contains the unsubscribed emails.")
    msg.attach(MIMEText(body, "plain"))

    with open(ATTACHMENT_FILE, "rb") as att:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(att.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition",
                        f"attachment; filename={ATTACHMENT_FILE}")
        msg.attach(part)

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
            s.starttls()
            s.login(SENDER_EMAIL, SENDER_PASSWORD)
            s.sendmail(SENDER_EMAIL, REPORT_EMAILS, msg.as_string())
        print("📧 Unsubscribe report emailed successfully.")
    except Exception as e:
        print(f"❌ Failed to send report: {e}")

    os.remove(ATTACHMENT_FILE) if os.path.exists(ATTACHMENT_FILE) else None

    # After sending, delete those unsubscribed > 12 hours old
    all_rows = read_unsubscribes()
    recent = [r for r in all_rows if datetime.fromisoformat(r[1]) > since]
    write_unsubscribes(recent)
    print("🧹 Cleaned old unsubscribes after sending report.")

# --------------------- Background Threads ---------------------
def periodic_tasks():
    """Run hourly cleanup and 12-hour report automatically."""
    last_report = datetime.utcnow()
    while True:
        time.sleep(3600)  # every hour
        # cleanup entries older than 48 hours (safety)
        rows = read_unsubscribes()
        fresh = [r for r in rows
                 if datetime.fromisoformat(r[1]) > datetime.utcnow() - timedelta(hours=48)]
        if len(fresh) != len(rows):
            write_unsubscribes(fresh)
            print("🧹 Removed unsubscribes older than 48 hours.")

        # send report every 12 hours
        if datetime.utcnow() - last_report >= timedelta(hours=12):
            send_unsubscribe_report()
            last_report = datetime.utcnow()

Thread(target=periodic_tasks, daemon=True).start()

# --------------------- Manual Trigger ---------------------
@app.route("/send_report")
def send_report():
    send_unsubscribe_report()
    return "✅ Unsubscribe report sent."

# --------------------- Start Server ---------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
