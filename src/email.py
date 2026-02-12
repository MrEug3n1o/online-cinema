import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.config import get_settings

settings = get_settings()


def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send an email using SMTP"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{settings.FROM_NAME} <{settings.FROM_EMAIL}>"
        msg['To'] = to_email

        html_part = MIMEText(body, 'html')
        msg.attach(html_part)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def send_activation_email(to_email: str, token: str) -> bool:
    """Send account activation email"""
    activation_link = f"{settings.FRONTEND_URL}/activate?token={token}"
    subject = "Activate Your Account - Online Cinema"
    body = f"""
    <html>
        <body>
            <h2>Welcome to Online Cinema!</h2>
            <p>Thank you for registering. Please activate your account by clicking the link below:</p>
            <p><a href="{activation_link}">Activate Account</a></p>
            <p>This link will expire in 24 hours.</p>
            <p>If you didn't create an account, please ignore this email.</p>
            <br>
            <p>Best regards,<br>Online Cinema</p>
        </body>
    </html>
    """
    return send_email(to_email, subject, body)


def send_password_reset_email(to_email: str, token: str) -> bool:
    """Send password reset email"""
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    subject = "Password Reset - Online Cinema"
    body = f"""
    <html>
        <body>
            <h2>Password Reset Request</h2>
            <p>You have requested to reset your password. Click the link below to set a new password:</p>
            <p><a href="{reset_link}">Reset Password</a></p>
            <p>This link will expire in 1 hour.</p>
            <p>If you didn't request a password reset, please ignore this email.</p>
            <br>
            <p>Best regards,<br>Online Cinema</p>
        </body>
    </html>
    """
    return send_email(to_email, subject, body)
