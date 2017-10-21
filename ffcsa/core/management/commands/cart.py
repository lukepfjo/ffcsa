import datetime

from cartridge.shop.models import Cart, Order, SelectedProduct
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.management import BaseCommand
from django.utils.timezone import now


class Command(BaseCommand):
    """
    take all carts, and create orders out of the cart.
    This is meant to be run as a cron job, to close the current weeks order
    """
    help = 'Convert current carts into orders'

    def handle(self, *args, **options):
        carts = Cart.objects.all()

        for cart in carts:
            if cart.has_items():
                print("cart has items")
                user = get_user_model().objects.get(id=cart.user_id)

                order_dict = {
                    'user_id': user.id,
                    # add 1 day since all billing is based off of Friday ordering, but orders close on Thursday
                    'time': now() + datetime.timedelta(days=1),
                    'site': Site.objects.get(id=1),
                    'billing_detail_first_name': user.first_name,
                    'billing_detail_last_name': user.last_name,
                    'billing_detail_email': user.email,
                    'billing_detail_phone': user.profile.phone_number,
                    'total': cart.total_price(),
                    'attending_dinner': cart.attending_dinner,
                    'drop_site': user.profile.drop_site
                }

                order = Order.objects.create(**order_dict)
                order.save()

                print("saved order")
                for item in cart:
                    product_fields = [f.name for f in SelectedProduct._meta.fields]
                    item_dict = dict([(f, getattr(item, f)) for f in product_fields])

                    # since we can't perform field injection on abstract classes we need to manually add
                    # any injected fields here

                    item_dict['category'] = item.category
                    item_dict['vendor'] = item.vendor

                    order.items.create(**item_dict)

                order.save()

            print("cart clear")
            cart.clear()
            cart.save()
