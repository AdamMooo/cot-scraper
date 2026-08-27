"""
Send the weekly report by email through Gmail SMTP.

Reads three environment variables, provided as GitHub Actions secrets so no
credential ever appears in code or logs:
    GMAIL_USER          -- the sending Gmail address
    GMAIL_APP_PASSWORD  -- a Google App Password (not the account password)
    MAIL_TO             -- recipient address

The HTML part is rendered from the report markdown by _markdown_to_html,
which handles exactly the constructs analysis.build_report emits (headings,
bullets, bold, pipe tables, horizontal rules). All styles are inline because
Gmail strips <style> blocks in many contexts; the plain-text part keeps the
raw markdown for clients that prefer it.

Public interface:
    send_email(subject, body_markdown) -> None
"""

import html
import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

_FONT = "-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
_TEXT = "color:#1f2937;"
_MUTED = "color:#6b7280;"
_POS = "#0a7d33"
_NEG = "#b42318"


def _inline(text: str) -> str:
    """Escape, then render **bold**. Order matters: escaping after would eat the tags."""
    out = html.escape(text, quote=False)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)


def _cell(text: str, header: bool = False) -> str:
    """One table cell. Numeric-looking cells right-align; signed values get colour."""
    value = text.strip()
    align = "right" if re.match(r"^[+\-]?\d|^n/a$", value) else "left"
    colour = ""
    if value.startswith("+"):
        colour = f"color:{_POS};"
    elif value.startswith("-") and value != "-":
        colour = f"color:{_NEG};"
    tag = "th" if header else "td"
    weight = "font-weight:600;" if header else ""
    return (f"<{tag} style=\"padding:5px 10px;border-bottom:1px solid #e5e7eb;"
            f"text-align:{align};{weight}{colour}white-space:nowrap;\">{_inline(value)}</{tag}>")


def _table(lines: list[str]) -> str:
    rows = [[c for c in line.strip().strip("|").split("|")] for line in lines]
    body = [r for r in rows[1:] if not all(re.fullmatch(r":?-+:?", c.strip()) for c in r)]
    out = [f"<table style=\"border-collapse:collapse;font-size:13px;{_TEXT}margin:8px 0 16px;\">",
           "<tr>" + "".join(_cell(c, header=True) for c in rows[0]) + "</tr>"]
    out += ["<tr>" + "".join(_cell(c) for c in r) + "</tr>" for r in body]
    out.append("</table>")
    return "\n".join(out)


def _markdown_to_html(md: str) -> str:
    blocks: list[str] = []
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
        elif stripped.startswith("|"):
            start = i
            while i < len(lines) and lines[i].strip().startswith("|"):
                i += 1
            blocks.append(_table(lines[start:i]))
        elif stripped.startswith("## "):
            blocks.append(f"<h2 style=\"font-size:16px;{_TEXT}margin:20px 0 6px;"
                          f"border-bottom:1px solid #e5e7eb;padding-bottom:4px;\">"
                          f"{_inline(stripped[3:])}</h2>")
            i += 1
        elif stripped.startswith("# "):
            blocks.append(f"<h1 style=\"font-size:20px;{_TEXT}margin:0 0 10px;\">"
                          f"{_inline(stripped[2:])}</h1>")
            i += 1
        elif stripped == "---":
            blocks.append("<hr style=\"border:none;border-top:1px solid #e5e7eb;margin:18px 0;\">")
            i += 1
        elif stripped.startswith("- "):
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(f"<li style=\"margin:3px 0;\">{_inline(lines[i].strip()[2:])}</li>")
                i += 1
            blocks.append(f"<ul style=\"font-size:14px;{_TEXT}margin:6px 0 12px;"
                          f"padding-left:22px;\">" + "".join(items) + "</ul>")
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not re.match(r"^(#|\||- |---$)", lines[i].strip()):
                para.append(lines[i].strip())
                i += 1
            # The footer caveat sits after the report's only <hr>; render it muted.
            style = _MUTED + "font-size:12px;" if any(b.startswith("<hr") for b in blocks) else _TEXT + "font-size:14px;"
            blocks.append(f"<p style=\"{style}margin:6px 0 12px;line-height:1.5;\">{_inline(' '.join(para))}</p>")
    return (f"<div style=\"font-family:{_FONT};max-width:760px;margin:0 auto;padding:16px;\">"
            + "\n".join(blocks) + "</div>")


def send_email(subject: str, body_markdown: str) -> None:
    user = os.environ["GMAIL_USER"]
    password = os.environ["GMAIL_APP_PASSWORD"]
    to_addr = os.environ["MAIL_TO"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_addr
    msg.attach(MIMEText(body_markdown, "plain"))
    msg.attach(MIMEText(_markdown_to_html(body_markdown), "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(user, password)
        server.sendmail(user, [to_addr], msg.as_string())
