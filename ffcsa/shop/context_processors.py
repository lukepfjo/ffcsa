from ffcsa.shop.orders import valid_order_period_for_user


def shop_globals(request):
    can_order = request.user.is_authenticated() and valid_order_period_for_user(request.user)
    return {"can_order": can_order}
