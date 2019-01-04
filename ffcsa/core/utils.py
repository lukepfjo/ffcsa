import datetime
from cartridge.shop.models import Order
from cartridge.shop import utils
from decimal import Decimal
from mezzanine.conf import settings
from . import models as ffcsa_models
from django.db import models

ORDER_CUTOFF_DAY = settings.ORDER_CUTOFF_DAY or 3

# only 6 days because we want to end on 1 day and start on the next. 7 days will start and end on the same week day
DAYS_IN_WEEK = 6


def get_friday_pickup_date():
    now = datetime.datetime.now()

    days_ahead = 4 - now.weekday()  # Friday is the 5th day
    if now.weekday() >= ORDER_CUTOFF_DAY:
        days_ahead += 7  # since order cutoff is past, add 7 days

    return now + datetime.timedelta(days_ahead)


def get_order_week_start():
    now = datetime.datetime.now()

    if now.weekday() < ORDER_CUTOFF_DAY:
        delta = ORDER_CUTOFF_DAY - now.weekday() - 1  # subtract 1 so we end the day of the cutoff day
        week_end = now + datetime.timedelta(delta)
        week_start = week_end - datetime.timedelta(DAYS_IN_WEEK)
    else:
        delta = now.weekday() - ORDER_CUTOFF_DAY
        week_start = now - datetime.timedelta(delta)

    return week_start


def next_weekday(d, weekday):
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return d + datetime.timedelta(days_ahead)


def get_orders(user):
    return Order.objects \
        .filter(user_id=user.id) \
        .filter(time__gte=datetime.date(2017, 12, 1)) # started calculating payments 12/1/2017


def get_order_total(user):
    total = get_orders(user) \
        .aggregate(total=models.Sum('total'))['total']

    if total is None:
        total = Decimal(0)

    return total


def get_payment_total(user):
    total = ffcsa_models.Payment.objects \
        .filter(user=user, pending=False) \
        .aggregate(total=models.Sum('amount'))['total']

    if total is None:
        total = Decimal(0)

    return total


def recalculate_remaining_budget(request):
    """
    utitlity function to attach the remaining budget as an attribute on the request.user

    This should be called after any cart modifications, as we take into account the request.cart.total_price()
    in the calculated remaining_budget
    """
    if not request.user.is_authenticated():
        return

    ytd_contrib = get_payment_total(request.user)
    ytd_ordered = get_order_total(request.user)
    if not ytd_ordered:
        ytd_ordered = Decimal(0)
    if not ytd_contrib:
        ytd_contrib = Decimal(0)

    # update remaining_budget
    request.session["remaining_budget"] = float("{0:.2f}".format(ytd_contrib - ytd_ordered - request.cart.total_price()))


# monkey patch the recalculate_cart function to update the User.remaining_budget so we don't
# have to calculate that every page load, but only when the cart is updated
original_recalculate_cart = utils.recalculate_cart


def recalculate_cart(request):
    original_recalculate_cart(request)
    recalculate_remaining_budget(request)


utils.recalculate_cart = recalculate_cart
