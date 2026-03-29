from dotenv import load_dotenv
load_dotenv()

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from config import RECIPIENT_EMAILS, YOUR_NAME

def send_email(jobs):
    if not jobs:
        print("No matching jobs found — skipping email.")
        return

    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    today = datetime.now().strftime("%B %d, %Y %I:%M %p")

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:900px;margin:auto;padding:16px">
        <h2 style="color:#2c3e50">🎯 Job Matches — {today}</h2>
        <p>Hi {YOUR_NAME.split()[0]}, found <b>{len(jobs)}</b> new matches for you.</p>

        <table style="width:100%;border-collapse:collapse;font-size:14px">
            <tr style="background:#2c3e50;color:white">
                <th style="padding:10px;text-align:left">Role</th>
                <th style="padding:10px;text-align:left">Company</th>
                <th style="padding:10px;text-align:left">Location</th>
                <th style="padding:10px;text-align:center">Score</th>
                <th style="padding:10px;text-align:left">Fits</th>
                <th style="padding:10px;text-align:left">Missing</th>
                <th style="padding:10px;text-align:left">Visa</th>
                <th style="padding:10px;text-align:center">Apply</th>
            </tr>
    """

    for i, job in enumerate(jobs):
        bg = "#f9f9f9" if i % 2 == 0 else "#ffffff"
        score = job.get("score", 0)
        score_color = "#27ae60" if score >= 8 else "#e67e22" if score >= 6 else "#e74c3c"
        visa = job.get("visa_note", "—")

        html += f"""
            <tr style="background:{bg};border-bottom:1px solid #eee">
                <td style="padding:10px;font-weight:bold">
                    {job.get('title', '')}
                </td>
                <td style="padding:10px">{job.get('company', '')}</td>
                <td style="padding:10px">{job.get('location', '')}</td>
                <td style="padding:10px;text-align:center">
                    <span style="background:{score_color};color:white;padding:3px 8px;border-radius:10px;font-weight:bold">
                        {score}/10
                    </span>
                </td>
                <td style="padding:10px;color:#27ae60">{job.get('what_fits', '')}</td>
                <td style="padding:10px;color:#e74c3c">{job.get('whats_missing', '')}</td>
                <td style="padding:10px;font-size:12px;color:#666">{visa}</td>
                <td style="padding:10px;text-align:center">
                    <a href="{job.get('apply_url', '#')}"
                       style="background:#2980b9;color:white;padding:6px 12px;border-radius:4px;text-decoration:none;white-space:nowrap">
                        Apply
                    </a>
                </td>
            </tr>
        """

    html += """
        </table>
        <p style="color:#999;font-size:12px;margin-top:16px">
            Sent by Job Alert Agent — runs every 15 min via GitHub Actions
        </p>
    </div>
    """

    subject = f"🎯 {len(jobs)} New Job Matches — {datetime.now().strftime('%b %d %I:%M %p')}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    from config import RECIPIENT_EMAILS
    msg["To"] = ", ".join(RECIPIENT_EMAILS)    
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, RECIPIENT_EMAILS, msg.as_string())
            print(f"✅ Email sent — {len(jobs)} matches")
    except Exception as e:
        print(f"❌ Email failed: {e}")