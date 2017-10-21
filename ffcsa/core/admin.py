from __future__ import unicode_literals

import csv
import tempfile
import zipfile
import math
import collections
from itertools import groupby

from decimal import Decimal

from copy import deepcopy
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.template.loader import get_template
from django.urls import reverse

from cartridge.shop.models import Category, Product, Order, ProductVariation
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
    writer.writerow(
        ['Order Date', 'Last Name', 'Drop Site', 'Vendor', 'Category', 'Item', 'SKU', 'Unit Price', 'FFCSA Unit Price',
         'Quantity', 'Total Price', 'FFCSA Total Price'])

    for order in queryset:
        try:
            user = get_user_model().objects.get(id=order.user_id)
        except User.DoesNotExist:
            pass
        last_name = user.last_name if user else "Deleted User"
        drop_site = user.profile.drop_site if user else "N/A"
        row_base = [order.time, last_name, drop_site]

        for item in order.items.all():
            row = row_base.copy()
            row.append(item.vendor)
            row.append(item.category)
            row.append(item.description)
            row.append(item.sku)
            row.append(item.unit_price)
            row.append(item.unit_price * Decimal(.8) if item.total_price else '')
            row.append(item.quantity)
            row.append(item.total_price)
            row.append(item.total_price * Decimal(.8) if item.total_price else '')

            writer.writerow(row)

    return response


export_as_csv.short_description = "Export As CSV"


def keySort(item):
    return math.floor(int(item.sku) / 1000) * 1000


def download_invoices(self, request, queryset):
    invoices = {}

    for order in queryset:
        context = {"order": order}
        context.update(order.details_as_dict())

        items = [i for i in order.items.all()]

        items.sort(key=keySort)

        grouper = groupby(items, keySort)
        grouped_items = collections.OrderedDict()

        for k, g in grouper:
            if not k in grouped_items:
                grouped_items[k] = []
            grouped_items[k] += list(g)

        context['grouped_items'] = grouped_items
        context['details_list'] = ["First name", "Last name", "Email", "Phone", ""]

        html = get_template("shop/order_packlist_pdf.html").render(context)
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


order_admin_fieldsets = deepcopy(base.OrderAdmin.fieldsets)
order_admin_fieldsets_fields_list = list(order_admin_fieldsets[2][1]["fields"])
order_admin_fieldsets_fields_list.insert(1, 'attending_dinner')
order_admin_fieldsets_fields_list.insert(2, 'drop_site')
order_admin_fieldsets[2][1]["fields"] = tuple(order_admin_fieldsets_fields_list)

class MyOrderAdmin(base.OrderAdmin):
    actions = [export_as_csv, download_invoices]
    fieldsets = order_admin_fieldsets

    def get_form(self, request, obj=None, **kwargs):
        form = super(MyOrderAdmin, self).get_form(request, obj, **kwargs)

        for name, field in form.base_fields.items():
            if name != 'billing_detail_first_name' and name != 'billing_detail_last_name':
                field.required = False
        return form

    def save_formset(self, request, form, formset, change):
        total = 0
        for item in formset.cleaned_data:
            if item['DELETE']:
                total -= item['id'].total_price
            else:
                item['total_price'] = item['unit_price'] * item['quantity']
                total += item['total_price']

        form.instance.total = total

        formset.save()
        form.instance.save()


class MyCategoryAdmin(base.CategoryAdmin):
    form = CategoryAdminForm


productvariation_fields = base.ProductVariationAdmin.fields
productvariation_fields.insert(4, "vendor")


class ProductVariationAdmin(base.ProductVariationAdmin):
    fields = productvariation_fields


class ProductAdmin(base.ProductAdmin):
    inlines = (base.ProductImageAdmin, ProductVariationAdmin)

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
