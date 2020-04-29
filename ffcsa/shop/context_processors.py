from ffcsa.core.dropsites import user_can_order


def shop_globals(request):
    can_order = request.user.is_authenticated() and user_can_order(request.user)
    return {"can_order": can_order}
