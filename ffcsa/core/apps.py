import sys

import logging
from django.apps import AppConfig
from django.core.mail import send_mail
from mezzanine.conf import settings

from ffcsa.core.google import authenticate

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    name = 'ffcsa.core'
    label = 'ffcsa_core'

    def ready(self):
        # We do this here b/c we only want this to be called when the server is started,
        # not when a management cmd is called
        if 'runserver' not in sys.argv:
            print('Returning & not authenticating google api')
            return True

        # attempt to authenticate google client on startup
        if getattr(settings, 'ENABLE_GOOGLE_INTEGRATION', True) and not authenticate():
            send_mail(
                "Failed Google Authentication %s" % settings.SITE_TITLE,
                "Failed to authenticate FFCSA google account. App most likely failed to start.",
                settings.DEFAULT_FROM_EMAIL,
                [settings.ACCOUNTS_APPROVAL_EMAILS],
                fail_silently=True,
            )
            logger.error('Failed to authenticate with Google. Google API access will not work.')
