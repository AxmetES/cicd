import smtplib
from email.mime.text import MIMEText

from app.config import settings


def send_verification_email(to_email: str, token: str):
    verify_url = f"{settings.FRONTEND_URL}/verify/{token}"

    msg = MIMEText(f"Подтверди регистрацию: {verify_url}", "html")
    msg["Subject"] = "Подтверди свой email"
    msg["From"] = settings.GMAIL_USER
    msg["To"] = to_email

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(settings.GMAIL_USER, settings.GMAIL_APP_PASSWORD)
        server.send_message(msg)