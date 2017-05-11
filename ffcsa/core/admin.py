from __future__ import unicode_literals

import csv
import tempfile
import zipfile

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.template.loader import get_template
from django.urls import reverse

from cartridge.shop.models import Category, Product, Order
from django.contrib import admin

from cartridge.shop import admin as base

from mezzanine.generic.models import ThreadedComment
from weasyprint import HTML

from ffcsa.core.availability import inform_user_product_unavailable
from ffcsa.core.forms import CategoryAdminForm


def export_as_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="ffcsa_order_export.csv"'

    writer = csv.writer(response)
    writer.writerow(['Order Date', 'First Name', 'Last Name', 'Item', 'Description', 'Category',
                     'Unit Price', 'Quantity', 'Total Price'])

    for order in queryset:
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


export_as_csv.short_description = "Export As CSV"


def download_invoices(self, request, queryset):
    invoices = {}

    for order in queryset:
        context = {"order": order}
        context.update(order.details_as_dict())
        html = get_template("shop/order_invoice_pdf.html").render(context)

        invoice = tempfile.SpooledTemporaryFile()
        HTML(string=html).write_pdf(invoice)
        invoices[order.id] = invoice
        # Reset file pointer
        invoice.seek(0)

    with tempfile.SpooledTemporaryFile() as tmp:
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as archive:
            for order_id, invoice in invoices.items():
                archive.writestr("ffcsa_order_{}.pdf".format(order_id), invoice.read())
                invoice.close()

        # Reset file pointer
        tmp.seek(0)

        # Write file data to response
        response = HttpResponse(tmp.read(), content_type='application/x-zip-compressed')
        response['Content-Disposition'] = 'attachment; filename="ffcsa_order_invoices.zip"'
        return response


download_invoices.short_description = "Download Invoices"


class MyOrderAdmin(base.OrderAdmin):
    actions = [export_as_csv, download_invoices]


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
