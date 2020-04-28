import datetime

from django.conf import settings

_DROPSITE_DICT = {}
DROPSITE_CHOICES = []

for dropsite in settings.DROPSITES:
    name = dropsite['name']
    DROPSITE_CHOICES.append((name, dropsite['description']))
    _DROPSITE_DICT[name] = dropsite


def is_valid_dropsite(user):
    return user.profile.home_delivery or user.profile.drop_site in _DROPSITE_DICT


def get_color(dropsite_name):
    if dropsite_name == 'Home Delivery':
        return 'purple'

    ds = _DROPSITE_DICT[dropsite_name]
    color = ds['color'] if ds else 'white'
    if not ds:
        strokeColor = 'white'
    else:
        strokeColor = color if color is not 'white' else 'black'

    return color, strokeColor


def user_can_order(user):
    if user.profile.home_delivery:
        return _home_delivery_can_order(user)

    for window in settings.ORDER_WINDOWS:
        if user.profile.drop_site in window['dropsites']:
            return _is_order_window(window)

    return False


def _home_delivery_can_order(user):
    zip = user.profile.get_delivery_zip()

    for window in settings.ORDER_WINDOWS:
        if zip in window['homeDeliveryZips']:
            return _is_order_window(window)

    return False


def _is_order_window(window):
    return _get_order_window_start(window) <= datetime.datetime.now() <= _get_order_window_end(window)


def _get_order_window_start(window):
    week_end = _get_order_window_end(window)
    week_start = _get_next_day(window['startDay'])

    if week_start >= week_end:
        week_start = week_start - datetime.timedelta(7)

    hour, minute = window['startTime'].split(':')
    return week_start.replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)


def _get_order_window_end(window):
    week_end = _get_next_day(window['endDay'])
    hour, minute = window['endTime'].split(':')
    return week_end.replace(hour=int(hour), minute=int(minute), second=59, microsecond=0)


def _get_next_day(day):
    """
    Returns a datetime in the future for the next day number (1 - 7 (Mon - Sun))
    """
    now = datetime.datetime.now()

    if now.isoweekday() <= day:
        delta = day - now.isoweekday()
    else:
        delta = 7 - (now.isoweekday() - day)
    return now + datetime.timedelta(delta)
