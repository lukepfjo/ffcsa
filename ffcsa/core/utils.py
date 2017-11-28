from cartridge.shop.models import Order
from mezzanine.conf import settings
from . import models as ffcsa_models
from django.db import models

ORDER_CUTOFF_DAY = settings.ORDER_CUTOFF_DAY or 3


def get_ytd_orders(user):
    return Order.objects \
        .filter(user_id=user.id) \
        .filter(time__gte=user.profile.csa_year_start_date())


def get_ytd_order_total(user):
    return get_ytd_orders(user) \
        .aggregate(total=models.Sum('total'))['total']


def get_ytd_payment_total(user):
    return ffcsa_models.Payment.objects \
        .filter(user=user) \
        .filter(date__gte=user.profile.csa_year_start_date()) \
        .aggregate(total=models.Sum('amount'))['total']
