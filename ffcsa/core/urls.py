from __future__ import unicode_literals

from cartridge.shop import views
from django.conf.urls import url
from django.conf.urls.i18n import i18n_patterns
from mezzanine.conf import settings
from mezzanine.core.views import page_not_found

from ffcsa.core.utils import order_week_context
from ffcsa.core.views import shop_home

_slash = "/" if settings.APPEND_SLASH else ""

urlpatterns = i18n_patterns(
    url("^$", shop_home, name="home"),
    url("^cart%s$" % _slash, views.cart, kwargs={'extra_context': order_week_context()}, name="shop_cart"),
    url("^checkout%s$" % _slash, page_not_found, name="shop_checkout"),
    url("^checkout/complete%s$" % _slash, page_not_found,
        name="shop_complete"),
)
