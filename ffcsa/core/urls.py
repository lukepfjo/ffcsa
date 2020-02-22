from __future__ import unicode_literals

from django.conf.urls import url
from django.conf.urls.i18n import i18n_patterns
from mezzanine.conf import settings
from mezzanine.core.views import page_not_found
from mezzanine.accounts.views import profile_update

from ffcsa.core import views

ACCOUNT_URL = getattr(settings, "ACCOUNT_URL", "/accounts/")
SIGNUP_URL = getattr(
    settings, "SIGNUP_URL", "/%s/signup/" % ACCOUNT_URL.strip("/")
)

_slash = "/" if settings.APPEND_SLASH else ""

urlpatterns = i18n_patterns(
    url("^$", views.shop_home, name="home"),
    url("^%s%s$" % (SIGNUP_URL.strip("/"), _slash), views.signup, name="mezzanine_signup"),
    url("^donate%s$" % _slash, views.donate, name="donate"),
    url("^stripe%s$" % _slash, views.stripe_webhooks),
    url("^accounts/update%s$" % _slash, profile_update, kwargs={"extra_context": {"title": "Account Settings"}}),
    url(r'^country-autocomplete/$', views.ProductAutocomplete.as_view(), name='product-autocomplete')
)
