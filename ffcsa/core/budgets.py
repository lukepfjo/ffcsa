from django.utils.log import DEFAULT_LOGGING
from django.core.cache import caches
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from cartridge.shop.models import Order

from .models import Payment

CACHE_ALIAS = "ffcsa.core.budgets"

cache = caches[CACHE_ALIAS]


def set_recalculate_budget(user_id):
    cache.set(user_id, True)


def recalculate_budget_for_user(user):
    if user is None or not user.is_authenticated():
        return False

    if cache.get(user.id):
        cache.delete(user.id)
        return True

    return False


@receiver(post_save, sender=Payment)
@receiver(post_delete, sender=Payment)
def payment_handler(**kwargs):
    print('running payment_handler %s' % kwargs)
    set_recalculate_budget(kwargs['instance'].user.id)


@receiver(post_save, sender=Order)
@receiver(post_delete, sender=Order)
def order_handler(**kwargs):
    print('running order_handler %s' % kwargs)
    set_recalculate_budget(kwargs['instance'].user_id)
