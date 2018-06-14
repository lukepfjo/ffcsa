from __future__ import unicode_literals

import csv
import tempfile
import zipfile
import collections
from itertools import groupby

from decimal import Decimal

from copy import deepcopy

from django.http import HttpResponse, HttpResponseRedirect
from django.template.loader import get_template
from django.urls import reverse

from cartridge.shop.models import Category, Product, Order, Sale, DiscountCode
from django.contrib import admin

from cartridge.shop import admin as base

from mezzanine.generic.models import ThreadedComment
from mezzanine.utils.static import static_lazy as static
from weasyprint import HTML

from ffcsa.core.availability import inform_user_product_unavailable
from ffcsa.core.forms import CategoryAdminForm, OrderAdminForm
from .models import Payment
from .utils import recalculate_remaining_budget

TWOPLACES = Decimal(10) ** -2


def export_as_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="ffcsa_order_export.csv"'

    writer = csv.writer(response)
    writer.writerow(
        ['Order Date', 'Last Name', 'Drop Site', 'Vendor', 'Category', 'Item', 'SKU', 'Member Price',
         'Vendor Price', 'Quantity', 'Member Total Price', 'Vendor Total Price'])

    for order in queryset:
        last_name = order.billing_detail_last_name
        drop_site = order.drop_site
        row_base = [order.time.date(), last_name, drop_site]

        for item in order.items.all():
            row = row_base.copy()
            row.append(item.vendor)
            row.append(item.category[0] if isinstance(item.category, (list, tuple)) else item.category)
            row.append(item.description)
            row.append(item.sku)
            row.append(item.unit_price.quantize(TWOPLACES) if item.unit_price else '')
            if item.vendor_price:
                row.append(item.vendor_price.quantize(TWOPLACES))
            else:
                row.append((item.unit_price * Decimal(.7)).quantize(TWOPLACES) if item.total_price else '')
            row.append(item.quantity)
            row.append(item.total_price.quantize(TWOPLACES) if item.total_price else '')
            if item.vendor_price:
                row.append((item.vendor_price * item.quantity).quantize(TWOPLACES))
            else:
                row.append((item.total_price * Decimal(.7)).quantize(TWOPLACES) if item.total_price else '')

            writer.writerow(row)

    return response


export_as_csv.short_description = "Export As CSV"

DEFAULT_GROUP_KEY = 99


def keySort(categories):
    def func(item):
        try:
            cat = categories.get(titles=item.category)

            # 0 is default, so don't sort
            if not cat.parent and cat.order_on_invoice != 0:
                return (cat.order_on_invoice, item.vendor, item.description)

            if cat.parent and cat.parent.category and cat.parent.category.order_on_invoice != 0:
                parent_order = cat.parent.category.order_on_invoice
                order = cat.order_on_invoice
                if order == 0:
                    order = DEFAULT_GROUP_KEY

                return (
                    int("{}{}".format(parent_order, order)),
                    item.vendor,
                    item.description
                )

        except Category.DoesNotExist:
            pass

        # just return a really high number for category
        return (DEFAULT_GROUP_KEY, item.vendor, item.description)

    return func


def download_invoices(self, request, queryset):
    invoices = {}
    categories = Category.objects.exclude(slug='weekly-box')

    for order in queryset.order_by('drop_site'):
        context = {"order": order}
        context.update(order.details_as_dict())

        items = [i for i in order.items.all()]

        items.sort(key=keySort(categories))

        grouper = groupby(items, keySort(categories))
        grouped_items = collections.OrderedDict()

        for k, g in grouper:
            k = int(k[0])
            if not k in grouped_items:
                grouped_items[k] = []
            grouped_items[k] += list(g)

        context['grouped_items'] = grouped_items
        context['details_list'] = ["First name", "Last name", "Email", "Phone", "Alt. Phone"]

        html = get_template("shop/order_packlist_pdf.html").render(context)
        invoice = tempfile.SpooledTemporaryFile()
        HTML(string=html).write_pdf(invoice)
        invoices["{}_{}".format(order.drop_site, order.id)] = invoice
        # Reset file pointer
        invoice.seek(0)

    with tempfile.SpooledTemporaryFile() as tmp:
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as archive:
            for id, invoice in invoices.items():
                archive.writestr("order_{}.pdf".format(id), invoice.read())
                invoice.close()

        # Reset file pointer
        tmp.seek(0)

        # Write file data to response
        response = HttpResponse(tmp.read(), content_type='application/x-zip-compressed')
        response['Content-Disposition'] = 'attachment; filename="ffcsa_order_invoices.zip"'
        return response


download_invoices.short_description = "Download Invoices"

order_admin_fieldsets = deepcopy(base.OrderAdmin.fieldsets)
order_admin_fieldsets_fields_billing_details_list = list(order_admin_fieldsets[0][1]["fields"])
order_admin_fieldsets_fields_billing_details_list.insert(0, 'order_date')
order_admin_fieldsets_fields_billing_details_list.insert(1, 'user')
order_admin_fieldsets[0][1]["fields"] = tuple(order_admin_fieldsets_fields_billing_details_list)
order_admin_fieldsets_fields_list = list(order_admin_fieldsets[2][1]["fields"])
order_admin_fieldsets_fields_list.insert(1, 'attending_dinner')
order_admin_fieldsets_fields_list.insert(2, 'drop_site')
order_admin_fieldsets[2][1]["fields"] = tuple(order_admin_fieldsets_fields_list)


class MyOrderAdmin(base.OrderAdmin):
    actions = [export_as_csv, download_invoices]
    fieldsets = order_admin_fieldsets
    form = OrderAdminForm

    def get_form(self, request, obj=None, **kwargs):
        form = super(MyOrderAdmin, self).get_form(request, obj, **kwargs)

        for name, field in form.base_fields.items():
            field.required = False

            if obj and name == 'user':
                field.disabled = True
                field.initial = obj.user_id
            if name == 'order_date':
                field.disabled = False
                if obj:
                    field.initial = obj.time.date()
                    field.disabled = True
        return form

    def save_formset(self, request, form, formset, change):
        total = 0
        for item in formset.cleaned_data:
            if not item['DELETE']:
                item['total_price'] = item['unit_price'] * item['quantity']
                total += item['total_price']

        form.instance.total = total

        formset.save()
        form.instance.save()
        recalculate_remaining_budget(request)


category_fields = base.CategoryAdmin.fields
category_fieldsets = deepcopy(base.CategoryAdmin.fieldsets)
category_fieldsets_fields_list = list(category_fieldsets[0][1]["fields"])
category_fieldsets_fields_list.append('order_on_invoice')
category_fieldsets[0][1]["fields"] = tuple(category_fieldsets_fields_list)


class MyCategoryAdmin(base.CategoryAdmin):
    form = CategoryAdminForm
    fieldsets = category_fieldsets


productvariation_fields = base.ProductVariationAdmin.fields
productvariation_fields.insert(4, "vendor")
# remove sale_price, sale_from, sale_to
productvariation_fields.pop(3)
productvariation_fields.pop(4)
productvariation_fields.pop(4)
productvariation_fields.insert(2, "vendor_price")


class ProductVariationAdmin(base.ProductVariationAdmin):
    fields = productvariation_fields


product_list_display = base.ProductAdmin.list_display
# remove sku, sale_price
product_list_display.pop(4)
product_list_display.pop(5)
product_list_display.insert(4, "vendor_price")

product_list_editable = base.ProductAdmin.list_editable
# remove sku, sale_price
product_list_editable.pop(2)
product_list_editable.pop(3)
product_list_editable.insert(2, "vendor_price")

product_list_filter = list(base.ProductAdmin.list_filter)
product_list_filter.append("variations__vendor")
product_list_filter = tuple(product_list_filter)

# add custom js & css overrides
css = list(base.ProductAdmin.Media.css['all'])
css.append(static('css/admin/product.css'))
base.ProductAdmin.Media.css['all'] = tuple(css)
js = list(base.ProductAdmin.Media.js)
js.append(static('js/admin/product_margins.js'))
base.ProductAdmin.Media.js = tuple(js)


def export_price_list(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="price_list.csv"'

    writer = csv.writer(response)
    writer.writerow(
        ['Product', 'Vendor', 'Available', 'Vendor Price', 'Member Price', '% Margin'])

    for product in queryset.order_by('variations__vendor', 'category', 'title'):
        row = [
            product.title,
            product.variations.first().vendor,
            product.available,
            product.vendor_price,
            product.unit_price
        ]

        if product.vendor_price and product.unit_price:
            row.append(
                ((product.unit_price - product.vendor_price) / product.unit_price * 100).quantize(0)
            )
        else:
            row.append("")

        writer.writerow(row)

    return response



class ProductAdmin(base.ProductAdmin):
    actions = [export_price_list]
    inlines = (base.ProductImageAdmin, ProductVariationAdmin)
    list_display = product_list_display
    list_editable = product_list_editable
    list_filter = product_list_filter

    def save_model(self, request, obj, form, change):
        """
        Inform customers when a product in their cart has become unavailable
        """
        super(ProductAdmin, self).save_model(request, obj, form, change)

        # obj.variations.all()[0].live_num_in_stock()

        if "available" in form.changed_data and not obj.available:
            cart_url = request.build_absolute_uri(reverse("shop_cart"))
            inform_user_product_unavailable(obj.sku, obj.title, cart_url)


class PaymentAdmin(admin.ModelAdmin):
    date_hierarchy = 'date'
    list_display = ('user', 'date', 'amount')
    list_filter = ("user", "date")

    actions = ['bulk_edit']

    def bulk_edit(self, request, queryset):
        selected = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)
        return HttpResponseRedirect(reverse('admin_bulk_payments') + "?ids=%s" % ",".join(selected))

    bulk_edit.short_description = "Edit selected payments"

    def save_model(self, request, obj, form, change):
        super(PaymentAdmin, self).save_model(request, obj, form, change)
        recalculate_remaining_budget(request)


admin.site.unregister(Order)
admin.site.register(Order, MyOrderAdmin)
admin.site.unregister(Category)
admin.site.register(Category, MyCategoryAdmin)
admin.site.unregister(Product)
admin.site.register(Product, ProductAdmin)

admin.site.register(Payment, PaymentAdmin)

# TODO remove all unnecessary admin menus
admin.site.unregister(ThreadedComment)
admin.site.unregister(Sale)
admin.site.unregister(DiscountCode)
