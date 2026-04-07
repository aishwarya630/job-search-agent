import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from config import RECIPIENT_EMAILS, YOUR_NAME

def send_email(matches, system_logs):
    if not matches: return

    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    today = datetime.now().strftime("%B %d, %I:%M %p")

    # Health Report Section
    log_items = "".join([f"<li>{log}</li>" for log in system_logs[-10:]]) # Last 10 logs
    
    html = f"""
    <div style="font-family:sans-serif; max-width:1100px; margin:auto;">
        <h2 style="color:#2c3e50;">🎯 New Matches Found — {today}</h2>
        
        <div style="background:#f4f7f6; padding:10px; border-radius:5px; border-left:4px solid #3498db;">
            <b>System Logs:</b>
            <ul style="font-size:12px; color:#666;">{log_items}</ul>
        </div>

        <p>Hi {YOUR_NAME}, here are your matches (Min Score: 6):</p>
        
        <table style="width:100%; border-collapse:collapse; font-size:13px;">
            <tr style="background:#2c3e50; color:white; text-align:left;">
                <th style="padding:10px;">Role & Company</th>
                <th style="padding:10px;">Score</th>
                <th style="padding:10px;">Why Apply</th>
                <th style="padding:10px;">Missing Skills</th>
                <th style="padding:10px; text-align:center;">Actions</th>
            </tr>
    """

    for i, job in enumerate(matches):
        bg = "#f9f9f9" if i % 2 == 0 else "#ffffff"
        score = job.get("score", 0)
        color = "#27ae60" if score >= 8 else "#e67e22"
        
        html += f"""
            <tr style="background:{bg}; border-bottom:1px solid #eee;">
                <td style="padding:10px;"><b>{job.get('title')}</b><br><span style="color:#666;">{job.get('company')}</span></td>
                <td style="padding:10px;"><span style="color:{color}; font-weight:bold;">{score}/10</span></td>
                <td style="padding:10px; font-style:italic;">{job.get('why_apply', 'AI matched based on skills')}</td>
                <td style="padding:10px; color:#e74c3c;">{job.get('whats_missing', 'None')}</td>
                <td style="padding:10px; text-align:center;">
                    <a href="{job.get('apply_url')}" style="color:#2980b9; text-decoration:none; font-weight:bold;">Apply Now</a><br>
                    <a href="https://github.com/{os.environ.get('GITHUB_REPOSITORY', 'your-user/your-repo')}/blob/main/dashboard_data.json" 
                       style="color:#27ae60; font-size:11px; text-decoration:none;">View Tracker</a>
                </td>
            </tr>
        """

    html += "</table></div>"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🎯 {len(matches)} New Jobs - {today}"
    msg["From"] = smtp_user
    msg["To"] = ", ".join(RECIPIENT_EMAILS)
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, RECIPIENT_EMAILS, msg.as_string())
    except Exception as e:
        print(f"❌ Email failed: {e}")