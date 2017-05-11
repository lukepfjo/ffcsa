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
                if cart.submitted:
                    user = get_user_model().objects.get(id=cart.user_id)

                    additional_inst = "Attending Dinner: {}".format(cart.attending_dinner) if cart.attending_dinner else ""


                    order_dict = {
                        'user_id': user.id,
                        'time': now(),
                        'site': Site.objects.get(id=1),
                        'billing_detail_first_name': user.first_name,
                        'billing_detail_last_name': user.last_name,
                        'billing_detail_email': user.email,
                        'total': cart.total_price(),
                        'additional_instructions': additional_inst
                    }

                    order = Order.objects.create(**order_dict)
                    order.save()

                    print("saved order")
                    for item in cart:
                        product_fields = [f.name for f in SelectedProduct._meta.fields]
                        item = dict([(f, getattr(item, f)) for f in product_fields])
                        order.items.create(**item)

                    order.save()

            print("cart clear")
            cart.clear()
            cart.save()

