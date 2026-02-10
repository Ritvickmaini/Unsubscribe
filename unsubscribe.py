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

# ===================== CONFIG =====================
REPORT_EMAILS = [
    "b2bgrowthexpo@gmail.com",
    "miltonkeynesexpo@gmail.com"
]

SMTP_SERVER = "mail.miltonkeynesexpo.com"
SMTP_PORT = 587
SENDER_EMAIL = "mike@miltonkeynesexpo.com"
SENDER_PASSWORD = "dvnn-&-((jdK"

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
        <h2>Already unsubscribed</h2>
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
    since = now - timedelta(hours=2)

    all_rows = read_unsubscribes()

    to_report = [
        r for r in all_rows
        if since <= datetime.fromisoformat(r[1]) <= now
    ]

    if not to_report:
        print("📭 No unsubscribes in last 2 hours")
        return

    # Write CSV attachment
    with open(ATTACHMENT_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["email", "timestamp"])
        writer.writerows(to_report)

    # Build email
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

        # DELETE only reported rows
        remaining = [r for r in all_rows if r not in to_report]
        write_unsubscribes(remaining)

    except Exception as e:
        print(f"❌ Report failed: {e}")

    finally:
        if os.path.exists(ATTACHMENT_FILE):
            os.remove(ATTACHMENT_FILE)

# ===================== MANUAL / CRON =====================
@app.route("/send_report")
def send_report():
    send_unsubscribe_report()
    return "✅ Unsubscribe report sent."

# ===================== START =====================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
