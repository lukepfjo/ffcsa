import datetime

from django.utils import formats
from mezzanine import template
from ffcsa.core.utils import ORDER_CUTOFF_DAY, DAYS_IN_WEEK, get_friday_pickup_date, get_order_week_start

register = template.Library()


@register.simple_tag()
def pickup_date_text():
    pickup = get_friday_pickup_date()
    delivery = pickup + datetime.timedelta(1)
    print('Testing pickup date')

    return "Weekly order for pickup {} & delivery {}".format(formats.date_format(pickup, "D F d"),
                                                             formats.date_format(delivery, "D F d"))


@register.simple_tag()
def order_week_start():
    week_start = get_order_week_start()

    return formats.date_format(week_start, "F d, Y")


@register.simple_tag()
def order_week_end():
    now = datetime.datetime.now()

    if now.weekday() < ORDER_CUTOFF_DAY:
        delta = ORDER_CUTOFF_DAY - now.weekday() - 1  # subtract 1 so we end the day of the cutoff day
        order_week_end = now + datetime.timedelta(delta)
    else:
        delta = now.weekday() - ORDER_CUTOFF_DAY
        order_week_end = now + datetime.timedelta(DAYS_IN_WEEK - delta)

    return formats.date_format(order_week_end, "F d, Y")


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def get_billing_detail_field(billing_detail_list, key):
    for (k, value) in billing_detail_list:
        if k == key:
            return value

    return None
