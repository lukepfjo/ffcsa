from mezzanine.utils.email import send_mail_template
from mezzanine.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand


class Command(BaseCommand):
    """
    Send a Reminder email to all active members
    This is meant to be run as a cron job
    """
    help = 'Send a reminder email to all active members'

    def handle(self, *args, **options):
        users = get_user_model().objects.get(is_active=True)
        user_emails = [u.email for u in users if u.email]

        send_mail_template(
            "Wednesday Reminder!",
            "ffcsa_core/reminder_email",
            settings.DEFAULT_FROM_EMAIL,
            settings.DEFAULT_FROM_EMAIL,
            fail_silently=False,
            addr_bcc=user_emails
        )
