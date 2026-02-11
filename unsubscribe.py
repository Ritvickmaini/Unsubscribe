import os
import csv
from datetime import datetime, timedelta
from flask import Flask, request, render_template_string, jsonify
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import urllib.parse
import re
from threading import Lock
import threading
import time

# ===================== CONFIG =====================
REPORT_EMAILS = [
    "b2bgrowthexpo@gmail.com",
    "miltonkeynesexpo@gmail.com",
    "santosh@b2bgrowthhub.com",
    "geeconglobal@gmail.com"
]

SMTP_SERVER = "mail.southamptonbusinessexpo.com"
SMTP_PORT = 587
SENDER_EMAIL = "mike@southamptonbusinessexpo.com"
SENDER_PASSWORD = "bi,dEd4qir.p"

CSV_FILE = "unsubscribes.csv"
ATTACHMENT_FILE = "unsubscribed_emails_report.csv"

# ===================== INIT =====================
app = Flask(__name__)
csv_lock = Lock()

EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
)

# Ensure CSV exists
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["email", "timestamp"])

# ===================== HELPERS =====================
def clean_email(raw_email: str) -> str | None:
    if not raw_email:
        return None
    email = urllib.parse.unquote_plus(raw_email).strip().lower()
    return email if EMAIL_PATTERN.match(email) else None


def read_unsubscribes():
    with csv_lock:
        with open(CSV_FILE, newline="") as f:
            reader = csv.reader(f)
            next(reader, None)
            return [row for row in reader if len(row) == 2]


def write_unsubscribes(rows):
    with csv_lock:
        with open(CSV_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["email", "timestamp"])
            writer.writerows(rows)

# ===================== ROUTES =====================
@app.route("/")
def home():
    return "✅ Unsubscribe server running.", 200


@app.route("/unsubscribe")
def unsubscribe():
    raw_email = request.args.get("email")
    email = clean_email(raw_email)

    if not email:
        return render_template_string("""
        <h2 style="color:red;">Invalid unsubscribe request</h2>
        """), 400

    rows = read_unsubscribes()

    if any(r[0] == email for r in rows):
        return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Already Unsubscribed</title>
</head>
<body style="
    font-family: Arial, Helvetica, sans-serif;
    background-color: #f7f7f7;
    margin: 0;
    padding: 0;
">
    <div style="
        max-width: 600px;
        margin: 80px auto;
        background: #ffffff;
        padding: 40px;
        text-align: center;
        border-radius: 8px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    ">
        <h2 style="
            color: #3498DB;
            margin-bottom: 20px;
        ">
            You’re already unsubscribed
        </h2>

        <p style="
            font-size: 18px;
            color: #333;
            margin-bottom: 10px;
        ">
            Our records show that this email address<br>
            has already been unsubscribed.
        </p>

        <p style="
            color: #555;
            font-size: 15px;
            line-height: 1.6;
        ">
            You won’t receive any further emails from us.
        </p>
    </div>
</body>
</html>
""")

    with csv_lock:
        with open(CSV_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([email, datetime.utcnow().isoformat()])

    return render_template_string(f"""
<!DOCTYPE html>
<html>
<head>
    <title>Unsubscribed</title>
</head>
<body style="
    font-family: Arial, Helvetica, sans-serif;
    background-color: #f7f7f7;
    margin: 0;
    padding: 0;
">
    <div style="
        max-width: 600px;
        margin: 80px auto;
        background: #ffffff;
        padding: 40px;
        text-align: center;
        border-radius: 8px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    ">
        <h2 style="
            color: #E74C3C;
            margin-bottom: 20px;
        ">
            You’ve been unsubscribed
        </h2>

        <p style="
            font-size: 18px;
            color: #333;
            margin-bottom: 10px;
        ">
            We're sorry to see you go,
            <strong>{email}</strong>.
        </p>

        <p style="
            color: #555;
            font-size: 15px;
            line-height: 1.6;
        ">
            You will no longer receive our emails.<br>
            If this was a mistake, you’re always welcome back.
        </p>
    </div>
</body>
</html>
""")



@app.route("/get_unsubscribes")
def get_unsubscribes():
    emails = [r[0] for r in read_unsubscribes()]
    return jsonify({
        "count": len(emails),
        "unsubscribed": emails
    })

# ===================== REPORT LOGIC =====================
def send_unsubscribe_report():
    now = datetime.utcnow()
    report_since = now - timedelta(hours=2)
    cleanup_before = now - timedelta(hours=12)

    all_rows = read_unsubscribes()

    to_report = []
    remaining_rows = []

    for r in all_rows:
        try:
            ts = datetime.fromisoformat(r[1])
        except:
            continue

        # Report last 2 hours
        if report_since <= ts <= now:
            to_report.append(r)

        # Keep only last 12 hours
        if ts >= cleanup_before:
            remaining_rows.append(r)

    if not to_report:
        print("📭 No unsubscribes in last 2 hours")
    else:
        # Write CSV attachment
        with open(ATTACHMENT_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["email", "timestamp"])
            writer.writerows(to_report)

        msg = MIMEMultipart()
        msg["Subject"] = f"Unsubscribe Report – Last 2 Hours ({len(to_report)})"
        msg["From"] = SENDER_EMAIL
        msg["To"] = ", ".join(REPORT_EMAILS)

        msg.attach(MIMEText(
            f"Attached unsubscribe report.\n\nTotal: {len(to_report)}",
            "plain"
        ))

        with open(ATTACHMENT_FILE, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={ATTACHMENT_FILE}"
            )
            msg.attach(part)

        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
                s.starttls()
                s.login(SENDER_EMAIL, SENDER_PASSWORD)
                s.sendmail(SENDER_EMAIL, REPORT_EMAILS, msg.as_string())

            print(f"📧 Report sent ({len(to_report)} unsubscribes)")

        except Exception as e:
            print(f"❌ Report failed: {e}")

        finally:
            if os.path.exists(ATTACHMENT_FILE):
                os.remove(ATTACHMENT_FILE)

    # 🔥 Cleanup older than 12 hours
    write_unsubscribes(remaining_rows)
    print(f"🧹 Cleaned old unsubscribes. Stored: {len(remaining_rows)}")
# ===================== MANUAL / CRON =====================
def auto_report_worker():
    print("🚀 Auto report worker started...")
    time.sleep(7200)  # wait 2 hours first
    while True:
        try:
            send_unsubscribe_report()
        except Exception as e:
            print(f"❌ Auto report error: {e}")
        
        time.sleep(7200)  # 2 hours (7200 seconds)

# ===================== START =====================
if __name__ == "__main__":
    # Start background auto-report thread
    threading.Thread(target=auto_report_worker, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
