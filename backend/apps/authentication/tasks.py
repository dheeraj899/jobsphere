from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_password_reset_email_task(email, reset_url):
    """Send password reset email asynchronously"""
    send_mail(
        'Password Reset Request',
        f'Click the link to reset your password: {reset_url}',
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    ) 