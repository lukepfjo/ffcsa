import sys
from django.apps import AppConfig
from django.core.mail import send_mail
from mezzanine.conf import settings

from ffcsa.core.google import authenticate


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
        if not authenticate():
            send_mail(
                "Failed Google Authentication %s" % settings.SITE_TITLE,
                "Failed to authenticate FFCSA google account. App most likely failed to start.",
                settings.DEFAULT_FROM_EMAIL,
                [settings.ACCOUNTS_APPROVAL_EMAILS],
                fail_silently=False,
            )
            raise Exception('Failed to authenticate with google. Google api access will not work.')
