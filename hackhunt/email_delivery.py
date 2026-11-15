"""Builds the digest (plain text + HTML) and sends it through Gmail SMTP."""

import smtplib
import ssl
from datetime import date
from email.message import EmailMessage
from html import escape

from .config import MailConfig
from .models import LAGOS, Hackathon

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def build_digest(top: list[Hackathon], more: list[Hackathon], closing: list[Hackathon],
                 errors: list[str], today: date) -> tuple[str, str, str]:
    """Returns (subject, text, html)."""
    new_count = len(top) + len(more)
    bits = [f"{new_count} new"] if new_count else []
    if closing:
        bits.append(f"{len(closing)} closing soon")
    subject = "hackhunt: " + (", ".join(bits) if bits else "nothing new") + (" (with errors)" if errors else "")

    text, body = [], []
    if top:
        text.append(f"TOP NEW HACKATHONS ({len(top)})\n")
        body.append(f"<h2>Top new hackathons ({len(top)})</h2><ol>")
        for h in top:
            details = " · ".join(x for x in [
                f"Deadline: {_deadline(h, today)}",
                f"Prize: {h.prize_text or 'none listed'}",
                f"Themes: {', '.join(h.themes)}" if h.themes else "",
            ] if x)
            text += [f"{h.title}  [score {h.score:g}]", f"  {h.url}", f"  {details}", f"  Why: {h.score_reason}", ""]
            body.append(
                f'<li style="margin-bottom:12px"><a href="{escape(h.url)}"><b>{escape(h.title)}</b></a>'
                f" — score {h.score:g}<br>{escape(details)}<br><i>Why: {escape(h.score_reason)}</i></li>"
            )
        body.append("</ol>")
    if more:
        text.append(f"ALSO NEW, LOWER SCORE ({len(more)})\n")
        body.append(f"<h3>Also new, lower score ({len(more)})</h3><ul>")
        for h in more:
            text.append(f"- {h.title} — score {h.score:g}, {_days(h, today)} — {h.url}")
            body.append(f'<li><a href="{escape(h.url)}">{escape(h.title)}</a> — score {h.score:g}, {_days(h, today)}</li>')
        text.append("")
        body.append("</ul>")
    if closing:
        text.append("CLOSING SOON\n")
        body.append("<h2>Closing soon</h2><ul>")
        for h in closing:
            text.append(f"- {h.title} — {_deadline(h, today)} — {h.url}")
            body.append(f'<li><a href="{escape(h.url)}">{escape(h.title)}</a> — {escape(_deadline(h, today))}</li>')
        text.append("")
        body.append("</ul>")
    if not (top or more or closing):
        text.append("Nothing new today.\n")
        body.append("<p>Nothing new today.</p>")
    if errors:
        text.append("PROBLEMS THIS RUN")
        text += [f"- {e}" for e in errors]
        body.append('<h3 style="color:#a00">Problems this run</h3><ul>')
        body += [f"<li>{escape(e)}</li>" for e in errors]
        body.append("</ul>")

    html_body = '<div style="font-family:sans-serif;max-width:680px">' + "".join(body) + "</div>"
    return subject, "\n".join(text).rstrip() + "\n", html_body


def send(mail: MailConfig, subject: str, text: str, html_body: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = mail.user
    msg["To"] = ", ".join(mail.to)
    msg.set_content(text)
    msg.add_alternative(html_body, subtype="html")
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30, context=ssl.create_default_context()) as smtp:
        smtp.login(mail.user, mail.password)
        smtp.send_message(msg)


def _days(h: Hackathon, today: date) -> str:
    days = h.days_left(today)
    if days is None:
        return "deadline unknown"
    if days == 0:
        return "closes today"
    return "1 day left" if days == 1 else f"{days} days left"


def _deadline(h: Hackathon, today: date) -> str:
    if h.deadline is not None:
        when = h.deadline.astimezone(LAGOS).strftime("%a %d %b, %H:%M WAT")
    elif h.end_date is not None:
        when = h.end_date.strftime("%a %d %b")
    else:
        return "unknown"
    return f"{when} ({_days(h, today)})"
