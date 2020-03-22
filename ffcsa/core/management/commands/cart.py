import datetime

from django.conf import settings
from django.db.models import Sum, OuterRef, Subquery, IntegerField

from ffcsa.shop.models import Cart, Order, ProductVariation, CartItem
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

        extra_items = ProductVariation.objects \
            .filter(extra__gt=0, id__in=CartItem.objects.values('variation_id').distinct()) \
            .annotate(total_ordered=Subquery(
            CartItem.objects
                .filter(variation_id=OuterRef('pk'))
                .values('variation_id')  # provides group by variation_id
                .annotate(total_ordered=Sum('vendors__quantity'))
                .values('total_ordered'),
            output_field=IntegerField(),
        ))

        extra_items = list(extra_items)
        if len(extra_items) > 0:
            order = Order(**{
                # add 1 day since all billing is based off of Friday ordering, but orders close on Thursday
                'time': now() + datetime.timedelta(days=1),
                'site': Site.objects.get(id=1),
                'billing_detail_first_name': 'FFCSA Extra Order',
                'allow_substitutions': True
            })
            # order.save()

            has_extra = False
            total = 0
            # We do the following b/c we want to use the logic in CartItem.update_quantity to
            # determine which vendor to order the extra from
            cart, created = Cart.objects.get_or_create(user_id=0)
            cart.clear()
            for variation in extra_items:
                extra = round(variation.extra / 100 * variation.total_ordered)

                if extra > 0:
                    has_extra = True
                    if not order.id:
                        order.save()
                    item = CartItem.objects.create(cart=cart, variation=variation)
                    item.update_quantity(extra)
                    order.items.create_from_cartitem(item)
                    total += item.total_price

            if has_extra:
                order.item_total = total
                order.total = total
                order.save()
            cart.delete()

        for cart in carts:
            if cart.has_items():
                print("cart has items")
                user = get_user_model().objects.get(id=cart.user_id)

                if not user.profile.start_date:
                    user.profile.start_date = now()

                drop_site = user.profile.drop_site
                if settings.HOME_DELIVERY_ENABLED and user.profile.home_delivery:
                    drop_site = 'Home Delivery'
                if cart.attending_dinner:
                    drop_site = 'Farm'

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
                    'item_total': cart.item_total_price(),
                    'discount_code': user.profile.discount_code.code if user.profile.discount_code else "",
                    'discount_total': cart.discount(),
                    'total': cart.total_price(),
                    'attending_dinner': cart.attending_dinner,
                    'drop_site': drop_site,
                    'additional_instructions': user.profile.invoice_notes,
                    'no_plastic_bags': user.profile.no_plastic_bags,
                    'allow_substitutions': user.profile.allow_substitutions,
                }

                if settings.HOME_DELIVERY_ENABLED and user.profile.home_delivery:
                    # ex address: 2050 Goodpasture Loop, Eugene, OR 97401, USA
                    address_components = user.profile.delivery_address.split(',')
                    order_dict.update(**{
                        'shipping_type': 'Home Delivery',
                        'shipping_total': cart.delivery_fee(),
                        'shipping_detail_street': address_components[0],
                        'shipping_detail_city': address_components[1],
                        'shipping_detail_state': 'OR',
                        'shipping_detail_postcode': address_components[2].split(' ')[1],
                        'shipping_instructions': user.profile.delivery_notes,
                    })

                order = Order.objects.create(**order_dict)
                order.save()

                for item in cart:
                    if not item.variation.weekly_inventory:
                        item.variation.reduce_stock(item.quantity)

                    order.items.create_from_cartitem(item)

                order.save()

            cart.clear()
            cart.save()
