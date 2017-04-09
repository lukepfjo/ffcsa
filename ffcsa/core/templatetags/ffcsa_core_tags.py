import datetime

from django.utils import formats
from mezzanine.conf import settings

from mezzanine import template

ORDER_CUTOFF_DAY = settings.ORDER_CUTOFF_DAY or 3
# only 6 days because we want to end on 1 day and start on the next. 7 days will start and end on the same week day
DAYS_IN_WEEK = 6

register = template.Library()


@register.simple_tag()
def order_week_start():
    now = datetime.datetime.now() - datetime.timedelta(3)

    if now.weekday() < ORDER_CUTOFF_DAY:
        delta = ORDER_CUTOFF_DAY - now.weekday() - 1  # subtract 1 so we end the day of the cutoff day
        week_end = now + datetime.timedelta(delta)
        week_start = week_end - datetime.timedelta(DAYS_IN_WEEK)
    else:
        delta = now.weekday() - ORDER_CUTOFF_DAY
        week_start = now - datetime.timedelta(delta)

    return formats.date_format(week_start, "F d, Y")


@register.simple_tag()
def order_week_end():
    now = datetime.datetime.now() - datetime.timedelta(3)

    if now.weekday() < ORDER_CUTOFF_DAY:
        delta = ORDER_CUTOFF_DAY - now.weekday() - 1  # subtract 1 so we end the day of the cutoff day
        order_week_end = now + datetime.timedelta(delta)
    else:
        delta = now.weekday() - ORDER_CUTOFF_DAY
        order_week_end = now + datetime.timedelta(DAYS_IN_WEEK - delta)

    return formats.date_format(order_week_end, "F d, Y")
