from django.db import transaction

from cartridge.shop.models import Cart, CartItem
from django.contrib.auth import get_user_model
from mezzanine.conf import settings
from mezzanine.utils.email import send_mail_template


# TODO change to variation
def inform_user_product_unavailable(sku, variation_name, cart_url):
    users_ids = Cart.objects.filter(items__sku=sku).values_list('user_id', flat=True)
    users = get_user_model().objects.filter(id__in=users_ids)

    if users:
        transaction.on_commit(lambda: send_unavailable_email([u.email for u in users], variation_name, cart_url))

        CartItem.objects.filter(sku=sku).delete()


def send_unavailable_email(bcc_addresses, product, cart_url):
    context = {
        'cart_url': cart_url,
        'product': product
    }
    send_mail_template(
        "[{}] Weekly Order Item unavailable".format(settings.SITE_TITLE),
        "ffcsa_core/send_unavailable_email",
        settings.DEFAULT_FROM_EMAIL,
        "Undisclosed Recipients <{}>".format(settings.DEFAULT_FROM_EMAIL),
        context=context,
        fail_silently=False,
        addr_bcc=bcc_addresses
    )
