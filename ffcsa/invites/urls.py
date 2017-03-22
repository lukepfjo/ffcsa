from __future__ import unicode_literals

from .views import signup
from django.conf.urls import url
from django.conf.urls.i18n import i18n_patterns

from mezzanine.conf import settings

ACCOUNT_URL = getattr(settings, "ACCOUNT_URL", "/accounts/")
SIGNUP_URL = getattr(
    settings, "SIGNUP_URL", "/%s/signup/" % ACCOUNT_URL.strip("/")
)

_slash = "/" if settings.APPEND_SLASH else ""

urlpatterns = i18n_patterns(
    url("^%s%s$" % (SIGNUP_URL.strip("/"), _slash),
        signup, name="mezzanine_signup"),
)
