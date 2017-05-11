from __future__ import unicode_literals

import csv

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.urls import reverse

from cartridge.shop.models import Category, Product, Order, ProductVariation
from django.contrib import admin

from cartridge.shop import admin as base

from mezzanine.generic.models import ThreadedComment

from ffcsa.core.availability import inform_user_product_unavailable
from ffcsa.core.forms import CategoryAdminForm, OrderExportForm


class MyOrderAdmin(base.OrderAdmin):
    change_list_template = 'admin/ffcsa_core/extras/orders_change_list.html'

    def changelist_view(self, request, extra_context=None):
        export_form = OrderExportForm(request.POST or None)
        if request.method == 'POST' and request.POST.get('export_orders'):
            if export_form.is_valid():
                orders = export_form.get_orders()

                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename="ffcsa_order_export.csv"'
                writer = csv.writer(response)
                # writer.writerow(['Order Date', 'First Name', 'Last Name', 'Item', 'Description', 'Category', 'Sub Category',
                #                  'Unit Price', 'Quantity', 'Total Price'])
                writer.writerow(['Order Date', 'First Name', 'Last Name', 'Item', 'Description', 'Category',
                                 'Unit Price', 'Quantity', 'Total Price'])

                for order in orders:
                    user = get_user_model().objects.get(id=order.user_id)
                    row_base = [order.time, user.first_name, user.last_name]

                    for item in order.items.all():
                        p = Product.objects.filter(sku=item.sku).first()

                        # category = p.categories.exclude(slug='weekly-box').first()
                        # sub_category = None

                        # if category.parent:
                        #     sub_category = category
                        #     category = sub_category.parent

                        row = row_base.copy()
                        row.append(item.description)
                        row.append(p.content)
                        row.append(",".join([c.titles for c in p.categories.exclude(slug='weekly-box')]))
                        # row.append(sub_category.title)
                        row.append(item.unit_price)
                        row.append(item.quantity)
                        row.append(item.total_price)

                        writer.writerow(row)

                return response

        context = {"export_form": export_form}
        context.update(extra_context or {})
        return super().changelist_view(request, context)


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


admin.site.unregister(Order)
admin.site.register(Order, MyOrderAdmin)
admin.site.unregister(Category)
admin.site.register(Category, MyCategoryAdmin)
admin.site.unregister(Product)
admin.site.register(Product, ProductAdmin)

# TODO remove all unecessary admin menus
admin.site.unregister(ThreadedComment)
