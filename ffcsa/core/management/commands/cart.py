import datetime

from cartridge.shop.models import Cart, Order, ProductVariation
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

                if not user.profile.start_date:
                    user.profile.start_date = now()

                order_dict = {
                    'user_id': user.id,
                    # add 1 day since all billing is based off of Friday ordering, but orders close on Thursday
                    'time': now() + datetime.timedelta(days=1),
                    'site': Site.objects.get(id=1),
                    'billing_detail_first_name': user.first_name,
                    'billing_detail_last_name': user.last_name,
                    'billing_detail_email': user.email,
                    'billing_detail_phone': user.profile.phone_number,
                    'billing_detail_phone_2': user.profile.phone_number_2,
                    'item_total': cart.total_price(),
                    'discount_code': user.profile.discount_code.code if user.profile.discount_code else "",
                    'discount_total': cart.discount(),
                    'total': cart.total_price_after_discount(),
                    'attending_dinner': cart.attending_dinner,
                    'drop_site': 'Farm' if cart.attending_dinner else user.profile.drop_site,
                    'additional_instructions': user.profile.invoice_notes,
                    'no_plastic_bags': user.profile.no_plastic_bags,
                    'allow_substitutions': user.profile.allow_substitutions,
                }

                order = Order.objects.create(**order_dict)
                order.save()

                print("saved order")
                for item in cart:
                    try:
                        variation = ProductVariation.objects.get(sku=item.sku)
                        if not variation.weekly_inventory:
                            variation.update_stock(item.quantity * -1)
                    except ProductVariation.DoesNotExist:
                        pass

                    order.items.create_from_cartitem(item)

                order.save()

            print("cart clear")
            cart.clear()
            cart.save()
