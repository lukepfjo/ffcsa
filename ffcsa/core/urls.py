from __future__ import unicode_literals

from django.conf.urls import url
from django.conf.urls.i18n import i18n_patterns

from ffcsa.core.views import shop_home

urlpatterns = i18n_patterns(
    url("^$", shop_home, name="home"),
)
