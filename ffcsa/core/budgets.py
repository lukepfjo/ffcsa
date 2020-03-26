import logging
from importlib import import_module

from django.contrib.auth import get_user_model
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from ffcsa.shop.models import Order, Cart
from mezzanine.conf import settings

from ffcsa.core.sessions import UserSession
from .models import Payment

logger = logging.getLogger(__name__)

engine = import_module(settings.SESSION_ENGINE)
SessionStore = engine.SessionStore

User = get_user_model()


def clear_cached_budget_for_variation(variation):
    carts = Cart.objects.filter(items__variation__sku=variation.sku)
    for cart in carts:
        clear_cached_budget_for_user_id(cart.user_id)


def clear_cached_budget_for_user_id(id):
    try:
        user = User.objects.get(pk=id)
        clear_cached_budget(user)
    except User.DoesNotExist:
        pass


def clear_cached_budget(user):
    # Users can have multiple sessions
    for userSession in UserSession.objects.filter(user=user):
        session = SessionStore(userSession.session_key)
        if session.exists(session.session_key):
            try:
                session['remaining_budget'] = None
                session.save()
            except Exception as e:
                logger.error(e)


@receiver(post_save, sender=Payment)
@receiver(post_delete, sender=Payment)
def payment_handler(**kwargs):
    clear_cached_budget(kwargs['instance'].user)


@receiver(post_save, sender=Order)
@receiver(post_delete, sender=Order)
def order_handler(**kwargs):
    clear_cached_budget_for_user_id(kwargs['instance'].user_id)
