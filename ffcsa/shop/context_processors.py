from __future__ import unicode_literals

from mezzanine.conf import settings

name = "ffcsa.shop.context_processors.shop_globals"
if name in settings.TEMPLATE_CONTEXT_PROCESSORS:
    from warnings import warn

    warn(name + " deprecated; use ffcsa.shop.middleware.ShopMiddleware")


    def shop_globals(request):
        return {"cart": request.cart}
