"""
Send the weekly report by email through Gmail SMTP.

Reads three environment variables, provided as GitHub Actions secrets so no
credential ever appears in code or logs:
    GMAIL_USER          -- the sending Gmail address
    GMAIL_APP_PASSWORD  -- a Google App Password (not the account password)
    MAIL_TO             -- recipient address

Public interface:
    send_email(subject, body_markdown) -> None
"""

import html
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(subject: str, body_markdown: str) -> None:
    user = os.environ["GMAIL_USER"]
    password = os.environ["GMAIL_APP_PASSWORD"]
    to_addr = os.environ["MAIL_TO"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_addr
    msg.attach(MIMEText(body_markdown, "plain"))
    msg.attach(MIMEText(
        f"<pre style='font-family: Consolas, monospace; white-space: pre-wrap;'>{html.escape(body_markdown)}</pre>",
        "html",
    ))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(user, password)
        server.sendmail(user, [to_addr], msg.as_string())
