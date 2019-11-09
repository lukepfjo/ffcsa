from django.conf import settings
import logging


class RequireRollbar(logging.Filter):
    def filter(self, record):
        return bool(settings.ROLLBAR['enabled'])
