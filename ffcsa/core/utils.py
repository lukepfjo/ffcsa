import datetime

import emoji as emoji
from mezzanine.conf import settings

ORDER_CUTOFF_DAY = 3

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


def next_weekday(d, weekday):
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return d + datetime.timedelta(days_ahead)


def get_next_day(day, from_day=None):
    """
    Returns a datetime in the future for the next day number (1 (Monday) - 7 (Sunday))
    """
    if from_day is None:
        from_day = datetime.datetime.now()

    if from_day.isoweekday() <= day:
        delta = day - from_day.isoweekday()
    else:
        delta = 7 - (from_day.isoweekday() - day)
    return from_day + datetime.timedelta(delta)
