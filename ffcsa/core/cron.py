import kronos
from cartridge.shop.models import Cart, Order, SelectedProduct

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.utils.timezone import now
from mezzanine.conf import settings

ORDER_CUTOFF_DAY = settings.ORDER_CUTOFF_DAY or 3


@kronos.register('1 0 * * {day}'.format(day=(ORDER_CUTOFF_DAY + 1)))
def close_order_job():
    """
    take all carts, and create orders out of the cart.
    This is meant to be run as a cron job, to close the current weeks order
    """
    carts = Cart.objects.all()

    for cart in carts:
        if cart.has_items():
            user = get_user_model().objects.get(id=cart.user_id)

            order_dict = {
                'user_id': user.id,
                'time': now(),
                'site': Site.objects.get(id=1),
                'billing_detail_first_name': user.first_name,
                'billing_detail_last_name': user.last_name,
            }

            order = Order.objects.create(**order_dict)
            order.save()

            for item in cart:
                product_fields = [f.name for f in SelectedProduct._meta.fields]
                item = dict([(f, getattr(item, f)) for f in product_fields])
                order.items.create(**item)

            order.save()
            cart.clear()
