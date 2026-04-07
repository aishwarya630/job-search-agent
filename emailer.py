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
    # Set this in your GitHub Secrets or hardcode it
    streamlit_link = os.environ.get("STREAMLIT_APP_URL", "https://job-search-agent-ash.streamlit.app/")
    
    today = datetime.now().strftime("%B %d, %I:%M %p")

    # Health Report Section
    log_items = "".join([f"<li>{log}</li>" for log in system_logs[-10:]]) 
    
    html = f"""
    <div style="font-family:sans-serif; max-width:1100px; margin:auto;">
        <h2 style="color:#2c3e50;">🎯 New Job Matches — {today}</h2>
        
        <div style="background:#f4f7f6; padding:10px; border-radius:5px; border-left:4px solid #3498db; margin-bottom:20px;">
            <b>System Health:</b>
            <ul style="font-size:11px; color:#666; margin-top:5px;">{log_items}</ul>
        </div>

        <p>Hi {YOUR_NAME}, I found {len(matches)} matches. Manage them in your 
           <a href="{streamlit_link}" style="color:#3498db; font-weight:bold;">Interactive CRM</a>.
        </p>
        
        <table style="width:100%; border-collapse:collapse; font-size:12px;">
            <tr style="background:#2c3e50; color:white; text-align:left;">
                <th style="padding:10px;">Role & Company</th>
                <th style="padding:10px;">Score</th>
                <th style="padding:10px;">Visa/Note</th>
                <th style="padding:10px;">Missing Skills</th>
                <th style="padding:10px; text-align:center;">Action</th>
            </tr>
    """

    for i, job in enumerate(matches):
        bg = "#f9f9f9" if i % 2 == 0 else "#ffffff"
        score = job.get("score", 0)
        color = "#27ae60" if score >= 8 else "#e67e22"
        
        html += f"""
            <tr style="background:{bg}; border-bottom:1px solid #eee;">
                <td style="padding:10px;">
                    <b>{job.get('title')}</b><br>
                    <span style="color:#666;">{job.get('company')} — {job.get('location')}</span>
                </td>
                <td style="padding:10px;"><span style="color:{color}; font-weight:bold;">{score}/10</span></td>
                <td style="padding:10px; font-size:11px; color:#555;">{job.get('visa_note', 'N/A')}</td>
                <td style="padding:10px; color:#e74c3c;">{job.get('whats_missing', 'None')}</td>
                <td style="padding:10px; text-align:center;">
                    <a href="{job.get('apply_url')}" 
                       style="display:inline-block; padding:5px 10px; background:#2980b9; color:white; text-decoration:none; border-radius:3px; font-weight:bold;">
                       Apply
                    </a>
                </td>
            </tr>
        """

    html += """
        </table>
        <div style="margin-top:20px; text-align:center; padding:20px; background:#eee; border-radius:5px;">
            <p style="margin:0; font-size:14px;">Want to change status or add notes?</p>
            <a href="{}" style="color:#2980b9; font-weight:bold; font-size:16px;">Go to Streamlit CRM Tracker →</a>
        </div>
    </div>
    """.format(streamlit_link)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🎯 {len(matches)} New Jobs - {today}"
    msg["From"] = smtp_user
    msg["To"] = ", ".join(RECIPIENT_EMAILS)
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, RECIPIENT_EMAILS, msg.as_string())
            print("📧 Email sent successfully.")
    except Exception as e:
        print(f"❌ Email failed: {e}")
