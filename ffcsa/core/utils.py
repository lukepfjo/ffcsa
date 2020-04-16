import datetime

import emoji as emoji
from mezzanine.conf import settings

ORDER_CUTOFF_DAY = settings.ORDER_CUTOFF_DAY or 3

# only 6 days because we want to end on 1 day and start on the next. 7 days will start and end on the same week day
DAYS_IN_WEEK = 6


def give_emoji_free_text(text):
    if not text:
        return text
    return emoji.get_emoji_regexp().sub(r'', text)


def get_current_friday_pickup_date():
    now = datetime.datetime.now()
    days_ahead = 4 - now.weekday()  # Friday is the 5th day
    return now + datetime.timedelta(days_ahead)


def get_friday_pickup_date():
    now = datetime.datetime.now()

    days_ahead = 4 - now.weekday()  # Friday is the 5th day
    if now.weekday() >= ORDER_CUTOFF_DAY:
        days_ahead += 7  # since order cutoff is past, add 7 days

    return now + datetime.timedelta(days_ahead)


def get_order_week_start():
    now = datetime.datetime.now()

    if now.weekday() < ORDER_CUTOFF_DAY:
        # subtract 1 so we end the day of the cutoff day
        delta = ORDER_CUTOFF_DAY - now.weekday() - 1
        week_end = now + datetime.timedelta(delta)
        week_start = week_end - datetime.timedelta(DAYS_IN_WEEK)
    else:
        delta = now.weekday() - ORDER_CUTOFF_DAY
        week_start = now - datetime.timedelta(delta)

    return week_start


def get_order_week_end():
    now = datetime.datetime.now()

    if now.weekday() < ORDER_CUTOFF_DAY:
        delta = ORDER_CUTOFF_DAY - now.weekday() - 1  # subtract 1 so we end the day of the cutoff day
        return now + datetime.timedelta(delta)
    else:
        delta = now.weekday() - ORDER_CUTOFF_DAY
        return now + datetime.timedelta(DAYS_IN_WEEK - delta)


def next_weekday(d, weekday):
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return d + datetime.timedelta(days_ahead)
