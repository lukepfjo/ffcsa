from __future__ import unicode_literals

from django.conf.urls import url
from django.conf.urls.i18n import i18n_patterns
from mezzanine.conf import settings

from ffcsa.core import views

_slash = "/" if settings.APPEND_SLASH else ""

urlpatterns = i18n_patterns(
    url(r'^dinner%s$' % _slash, views.admin_attending_dinner, name="admin_attending_dinner"),
    url(r'^budgets%s$' % _slash, views.admin_member_budgets, name="admin_member_budget"),
    url(r'^orders/recent%s$' % _slash, views.member_order_history, name="admin_member_order_history"),
    url(r'^ffcsa_core/payment/bulk%s$' % _slash, views.admin_bulk_payments, name="admin_bulk_payments"),
)
