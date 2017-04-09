from __future__ import unicode_literals

from django.urls import reverse

from cartridge.shop.models import Category, Product
from django.contrib import admin

from cartridge.shop import admin as base

from mezzanine.generic.models import ThreadedComment

from ffcsa.core.availability import inform_user_product_unavailable
from ffcsa.core.forms import CategoryAdminForm


class MyCategoryAdmin(base.CategoryAdmin):
    form = CategoryAdminForm


class ProductAdmin(base.ProductAdmin):
    def save_model(self, request, obj, form, change):
        """
        Inform customers when a product in their cart has become unavailable
        """
        super(ProductAdmin, self).save_model(request, obj, form, change)

        if "available" in form.changed_data and not obj.available:
            cart_url = request.build_absolute_uri(reverse("shop_cart"))
            inform_user_product_unavailable(obj.sku, obj.title, cart_url)


admin.site.unregister(Category)
admin.site.register(Category, MyCategoryAdmin)
admin.site.unregister(Product)
admin.site.register(Product, ProductAdmin)

# TODO remove all unecessary admin menus
admin.site.unregister(ThreadedComment)
