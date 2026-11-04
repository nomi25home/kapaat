import logging
import smtplib
from email.message import EmailMessage

from ..config import get_settings

log = logging.getLogger("kapaat.mail")


def send_login_code(email: str, code: str) -> None:
    s = get_settings()
    if s.mail_backend != "smtp":
        log.warning("Login code for %s: %s", email, code)
        return
    msg = EmailMessage()
    msg["Subject"] = f"Your Kapaat sign-in code: {code}"
    msg["From"] = s.smtp_from
    msg["To"] = email
    msg.set_content(
        f"Your Kapaat sign-in code is {code}\n\n"
        "It expires in 10 minutes. If you didn't try to sign in, ignore this email.\n"
    )
    with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as smtp:
        if s.smtp_starttls:
            smtp.starttls()
        if s.smtp_user:
            smtp.login(s.smtp_user, s.smtp_password)
        smtp.send_message(msg)
