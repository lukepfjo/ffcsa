from collections import Set

from django.conf import settings
from django.db import connection

from ffcsa.core.utils import get_next_day

_DROPSITE_DICT = {}
DROPSITE_CHOICES = []

for dropsite in settings.DROPSITES:
    name = dropsite['name']
    DROPSITE_CHOICES.append((name, dropsite['description']))
    _DROPSITE_DICT[name] = dropsite


def is_valid_dropsite(user):
    return user.profile.home_delivery or user.profile.drop_site in _DROPSITE_DICT


def get_pickup_date(user):
    from ffcsa.shop.orders import get_order_period_for_user
    week_start, week_end = get_order_period_for_user(user)

    if user.profile.home_delivery:
        zip = user.profile.delivery_address.zip
        day = settings.HOME_DELIVERY_DAY[zip] if zip in settings.HOME_DELIVERY_DAY else settings.HOME_DELIVERY_DAY[
            'default']
    else:
        day = _DROPSITE_DICT[user.profile.drop_site]['pickupDay']

    return get_next_day(day, week_start)


def get_full_drop_locations():
    """
    get a list of full locations. A Location is considered to be full
    if the limit has been reached for that specific location, or if
    the limit has been reached for a group of locations that contain
    the location.

    A location is either a dropsite, or a zip code for home delivery

    :return: list of locations that are full
    """
    cursor = connection.cursor()
    cursor.execute('''
    select p.drop_site, count(*)
      from ffcsa_core_profile p 
      where home_delivery = false and (
        (`stripe_subscription_id` is not null and `stripe_subscription_id` <> '') 
        or user_id in (select distinct(user_id) from shop_order where time >= date_sub(now(), interval 1 month))
      ) 
      group by p.drop_site
    union
    select a.zip, count(*)
    from ffcsa_core_profile p 
      join ffcsa_core_address a on p.delivery_address_id = a.id 
      where home_delivery = true and (
        (`stripe_subscription_id` is not null and `stripe_subscription_id` <> '')
        or user_id in (select distinct(user_id) from shop_order where time >= date_sub(now(), interval 1 month))
      ) 
    group by a.zip
    ''')

    location_counts = {}
    full_locations = set()
    for l, count in cursor:
        location_counts[l] = count
        # check if a given dropsite is full
        if l in _DROPSITE_DICT:
            limit = _DROPSITE_DICT[l]['memberLimit']
            if limit is not None and limit <= count:
                full_locations.add(l)
        elif l in settings.HOME_DELIVERY_ZIP_LIMITS:
            if settings.HOME_DELIVERY_ZIP_LIMITS[l] <= count:
                full_locations.add(l)

    # check if a location group is full
    for group in settings.DROP_LOCATION_GROUP_LIMITS:
        total = 0
        for l in group['locations']:
            if l in location_counts:
                total = total + location_counts[l]

            if total >= group['limit']:
                full_locations.update(group['locations'])
                break

    return list(full_locations)


def get_color(dropsite_name):
    if dropsite_name == 'Home Delivery':
        return 'purple', 'black'

    ds = _DROPSITE_DICT[dropsite_name]
    color = ds['color'] if ds else 'white'
    if not ds:
        strokeColor = 'white'
    else:
        strokeColor = color if color is not 'white' else 'black'

    return color, strokeColor
