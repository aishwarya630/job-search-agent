from dotenv import load_dotenv
load_dotenv()

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from config import RECIPIENT_EMAILS, YOUR_NAME

def send_email(matches, system_logs):
    # 1. FIX: Ensure we use 'matches' instead of 'jobs'
    if not matches and not system_logs:
        print("No matching jobs and no logs — skipping email.")
        return

    # 2. Format the Health Report Logs
    log_items = "".join([f"<li style='margin-bottom:4px'>{log}</li>" for log in system_logs])
    health_report_html = f"""
    <div style="background:#f4f7f6; padding:12px; border-radius:8px; margin-bottom:20px; border-left:4px solid #3498db">
        <h3 style="margin-top:0; color:#2c3e50; font-size:16px">📡 System Health Report</h3>
        <ul style="font-size:13px; color:#555; padding-left:20px; margin-bottom:0">
            {log_items if system_logs else "<li>All systems operational.</li>"}
        </ul>
    </div>
    """

    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    today = datetime.now().strftime("%B %d, %Y %I:%M %p")

    # Start Building HTML
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:1000px;margin:auto;padding:16px">
        <h2 style="color:#2c3e50">🎯 Job Matches — {today}</h2>
        
        {health_report_html}

        <p>Hi {YOUR_NAME.split()[0]}, found <b>{len(matches)}</b> new matches scoring 6+ for you.</p>
    """

    # Only add the table if there are actual matches
    if matches:
        html += """
        <table style="width:100%;border-collapse:collapse;font-size:13px">
            <tr style="background:#2c3e50;color:white">
                <th style="padding:10px;text-align:left">Role</th>
                <th style="padding:10px;text-align:left">Company</th>
                <th style="padding:10px;text-align:center">Score</th>
                <th style="padding:10px;text-align:left">Fits</th>
                <th style="padding:10px;text-align:left">Missing</th>
                <th style="padding:10px;text-align:left">Visa/Note</th>
                <th style="padding:10px;text-align:center">Link</th>
            </tr>
        """

        for i, job in enumerate(matches):
            bg = "#f9f9f9" if i % 2 == 0 else "#ffffff"
            score = job.get("score", 0)
            score_color = "#27ae60" if score >= 8 else "#e67e22" if score >= 6 else "#e74c3c"
            visa = job.get("visa_note", "—")

            html += f"""
                <tr style="background:{bg};border-bottom:1px solid #eee">
                    <td style="padding:10px;font-weight:bold">{job.get('title', '')}</td>
                    <td style="padding:10px">{job.get('company', '')}</td>
                    <td style="padding:10px;text-align:center">
                        <span style="background:{score_color};color:white;padding:3px 8px;border-radius:10px;font-weight:bold">
                            {score}/10
                        </span>
                    </td>
                    <td style="padding:10px;color:#27ae60">{job.get('what_fits', '')}</td>
                    <td style="padding:10px;color:#e74c3c">{job.get('whats_missing', '')}</td>
                    <td style="padding:10px;font-size:11px;color:#666">{visa}</td>
                    <td style="padding:10px;text-align:center">
                        <a href="{job.get('apply_url', '#')}" style="background:#2980b9;color:white;padding:5px 10px;border-radius:4px;text-decoration:none">Apply</a>
                    </td>
                </tr>
            """
        html += "</table>"
    else:
        html += "<p style='color:#666; font-style:italic;'>No new high-scoring matches in this window.</p>"

    html += """
        <p style="color:#999;font-size:11px;margin-top:20px;border-top:1px solid #eee;padding-top:10px">
            Sent by Job Alert Agent — Monitoring Google, LinkedIn, and Indeed every 15 min.
        </p>
    </div>
    """

    # Email Logic
    subject = f"🎯 {len(matches)} New Matches — {datetime.now().strftime('%I:%M %p')}"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = ", ".join(RECIPIENT_EMAILS)    
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, RECIPIENT_EMAILS, msg.as_string())
            print(f"✅ Email sent — {len(matches)} matches & health report.")
    except Exception as e:
        print(f"❌ Email failed: {e}")