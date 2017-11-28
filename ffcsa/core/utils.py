from datetime import datetime, timedelta
import calendar
from cartridge.shop.models import Order
from mezzanine.conf import settings

ORDER_CUTOFF_DAY = settings.ORDER_CUTOFF_DAY or 3


def get_ytd_orders(user):
    start_date = user.profile.start_date if user.profile.start_date else user.date_joined

    return Order.objects \
        .filter(user_id=user.id) \
        .filter(time__gte=start_date)


def get_start_day_of_month():
    """
    get the first day of the ordering period for the current month.

    ordering period is determined by the first friday of the month. if the coming friday is in the next month,
    then are ordering period is for next month. Otherwise our ordering period is for this month
    :return:
    """
    now = datetime.now()

    end_of_current_month = calendar.monthrange(now.year, now.month)[1]

    if now.date > end_of_current_month - ORDER_CUTOFF_DAY - 7:
        pass
    if now.day >= ORDER_CUTOFF_DAY:
        offset = ORDER_CUTOFF_DAY
        pass
    # else:

    if now.day > 21:
        # TODO need to check if we are on next month for orders
        pass
    first_day_of_month = datetime(now.year, now.month, 1)
    # 4 is day of week (friday)
    first_friday = first_day_of_month + timedelta(days=((4 - calendar.monthrange(now.year, now.month)[0]) + 7) % 7)
    third_friday = first_friday + timedelta(days=14)
