"""
📧 Email Helper para Sofia Web
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_HOST = os.getenv('SMTP_HOST', 'smtp-relay.brevo.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
SMTP_FROM_EMAIL = os.getenv('SMTP_FROM_EMAIL', 'contato@libernet.app')
SMTP_FROM_NAME = os.getenv('SMTP_FROM_NAME', 'Sofia AI')


def send_email(to: str, subject: str, body: str, html: str = None) -> bool:
    """Envia e-mail via Brevo"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f'{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>'
        msg['To'] = to

        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        if html:
            msg.attach(MIMEText(html, 'html', 'utf-8'))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        print(f"✅ E-mail enviado para {to}")
        return True
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


def send_password_reset(to: str, reset_link: str) -> bool:
    """E-mail de recuperação de senha"""
    subject = "Recuperação de Senha - Sofia AI"
    body = f"Clique no link para redefinir sua senha: {reset_link}"
    html = f"<p>Clique <a href='{reset_link}'>aqui</a> para redefinir sua senha.</p>"
    return send_email(to, subject, body, html)


def send_token_warning(to: str, username: str, tokens_left: int) -> bool:
    """Aviso de tokens acabando"""
    subject = "Atenção: Seus tokens estão acabando"
    body = f"Olá {username}, você tem {tokens_left} tokens restantes."
    html = f"<p>Olá <strong>{username}</strong>, você tem <strong>{tokens_left}</strong> tokens restantes.</p>"
    return send_email(to, subject, body, html)
