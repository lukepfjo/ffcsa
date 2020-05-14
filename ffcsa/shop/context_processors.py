from ffcsa.core.dropsites import is_valid_dropsite
from ffcsa.shop.orders import valid_order_period_for_user


def shop_globals(request):
    return {
        "can_order": request.user.is_authenticated() and valid_order_period_for_user(request.user),
        "valid_dropsite": request.user.is_authenticated() and is_valid_dropsite(request.user)
    }
