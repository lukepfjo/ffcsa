from django.urls import reverse
from mezzanine.conf import settings
from mezzanine.core.request import current_request
from mezzanine.utils.email import send_mail_template


def send_unavailable_email(variation, quantity=None, to_addr=None, bcc_addresses=None):
    if to_addr is None:
        to_addr = "Undisclosed Recipients <{}>".format(settings.DEFAULT_FROM_EMAIL),

    context = {
        'cart_url': current_request().build_absolute_uri(reverse("shop_cart")),
        'variation': variation,
        'quantity': quantity
    }
    send_mail_template(
        "[{}] Weekly Order Item Unavailable".format(settings.SITE_TITLE),
        "ffcsa_core/send_unavailable_email",
        settings.DEFAULT_FROM_EMAIL,
        to_addr,
        context=context,
        fail_silently=False,
        addr_bcc=bcc_addresses
    )
