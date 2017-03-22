import datetime

CUTOFF_DAY = 3
# only 6 days because we want to end on 1 day and start on the next. 7 days will start and end on the same week day
DAYS_IN_WEEK = 6


def order_week_context():
    now = datetime.datetime.now()

    if now.weekday() < CUTOFF_DAY:
        delta = CUTOFF_DAY - now.weekday() - 1  # subtract 1 so we end the day of the cutoff day
        order_week_end = now + datetime.timedelta(delta)
        order_week_start = order_week_end - datetime.timedelta(DAYS_IN_WEEK)
    else:
        delta = now.weekday() - CUTOFF_DAY
        order_week_start = now - datetime.timedelta(delta)
        order_week_end = now + datetime.timedelta(DAYS_IN_WEEK - delta)

    return {
        'order_week_start': order_week_start,
        'order_week_end': order_week_end,
    }
