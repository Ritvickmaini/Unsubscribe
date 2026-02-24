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
def clean_email(raw_email: str):
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


@app.route("/unsubscribe", methods=["GET", "POST"])
def unsubscribe():

    if request.method == "POST":
        raw_email = request.form.get("email")
        email = clean_email(raw_email)

        if not email:
            return render_template_string("""
            <h2 style="color:red;">Invalid email address</h2>
            <a href="/unsubscribe">Go Back</a>
            """)

        rows = read_unsubscribes()

        if any(r[0] == email for r in rows):
            return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Already Unsubscribed</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

body {
    height: 100vh;
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
    display: flex;
    align-items: center;
    justify-content: center;
}

.card {
    background: #ffffff;
    width: 100%;
    max-width: 420px;
    padding: 40px;
    border-radius: 16px;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.25);
    text-align: center;
}

.icon {
    font-size: 50px;
    margin-bottom: 15px;
}

h2 {
    margin-bottom: 10px;
    color: #2980b9;
}

p {
    font-size: 14px;
    color: #555;
}
</style>
</head>

<body>

<div class="card">
    <div class="icon">ℹ️</div>
    <h2>Already Unsubscribed</h2>
    <p>This email address is already removed from our mailing list.</p>
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
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Unsubscribed | B2B Growth Expo</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
* {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}}

body {{
    height: 100vh;
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
    display: flex;
    align-items: center;
    justify-content: center;
}}

.card {{
    background: #ffffff;
    width: 100%;
    max-width: 420px;
    padding: 40px;
    border-radius: 16px;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.25);
    text-align: center;
    animation: fadeIn 0.6s ease-in-out;
}}

.success-icon {{
    font-size: 50px;
    margin-bottom: 15px;
}}

h2 {{
    margin-bottom: 10px;
    color: #27ae60;
}}

p {{
    font-size: 14px;
    color: #555;
    margin-bottom: 25px;
}}

.button {{
    display: inline-block;
    padding: 12px 20px;
    border-radius: 8px;
    background: #2c5364;
    color: white;
    text-decoration: none;
    font-weight: 600;
    transition: 0.3s;
}}

.button:hover {{
    background: #203a43;
}}

@keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(15px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}
</style>
</head>

<body>

<div class="card">
    <div class="success-icon">✅</div>
    <h2>You’ve Been Unsubscribed</h2>
    <p><strong>{email}</strong><br>has been removed from our mailing list.</p>

</div>

</body>
</html>
""")

    # GET request → show form
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Unsubscribe | B2B Growth Expo</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        body {
            height: 100vh;
            background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .card {
            background: #ffffff;
            width: 100%;
            max-width: 420px;
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.25);
            text-align: center;
            animation: fadeIn 0.6s ease-in-out;
        }

        h2 {
            margin-bottom: 15px;
            color: #2c3e50;
        }

        p {
            font-size: 14px;
            color: #666;
            margin-bottom: 25px;
        }

        input[type="email"] {
            width: 100%;
            padding: 14px;
            border-radius: 8px;
            border: 1px solid #ddd;
            font-size: 15px;
            margin-bottom: 20px;
            transition: 0.3s;
        }

        input[type="email"]:focus {
            border-color: #2c5364;
            outline: none;
            box-shadow: 0 0 0 3px rgba(44, 83, 100, 0.2);
        }

        button {
            width: 100%;
            padding: 14px;
            border-radius: 8px;
            border: none;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            background: #2c5364;
            color: white;
            transition: 0.3s;
        }

        button:hover {
            background: #203a43;
            transform: translateY(-2px);
        }

        .footer {
            margin-top: 20px;
            font-size: 12px;
            color: #999;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(15px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @media (max-width: 480px) {
            .card {
                margin: 20px;
                padding: 30px;
            }
        }
    </style>
</head>
<body>

    <div class="card">
        <h2>Unsubscribe from Emails</h2>
        <p>Enter your email address below to stop receiving communications from us.</p>

        <form method="POST">
            <input 
                type="email" 
                name="email" 
                placeholder="your@email.com" 
                required
            >

            <button type="submit">
                Unsubscribe
            </button>
        </form>

        <div class="footer">
            B2B Growth Expo © 2026
        </div>
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

@app.route("/send_report_now")
def send_report_now():
    try:
        send_unsubscribe_report()
        return "✅ Report triggered successfully.", 200
    except Exception as e:
        return f"❌ Failed to send report: {e}", 500

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
