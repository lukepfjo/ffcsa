from __future__ import unicode_literals

import csv
import tempfile
import zipfile
import collections
import stripe
from itertools import groupby

from decimal import Decimal

from copy import deepcopy

from cartridge.shop.forms import ImageWidget
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.db.models import F, ImageField
from django.http import HttpResponse, HttpResponseRedirect
from django.template.loader import get_template
from django.urls import reverse

from cartridge.shop.models import Category, Product, Order, Sale, DiscountCode, CartItem
from django.contrib import admin

from cartridge.shop import admin as base
from mezzanine.accounts import admin as accounts_base

from mezzanine.conf import settings
from mezzanine.core.admin import SitePermissionInline
from mezzanine.core.models import CONTENT_STATUS_PUBLISHED
from mezzanine.generic.models import ThreadedComment
from mezzanine.pages.admin import PageAdmin
from mezzanine.utils.static import static_lazy as static
from weasyprint import HTML

from ffcsa.core.availability import inform_user_product_unavailable
from ffcsa.core.forms import CategoryAdminForm, OrderAdminForm
from ffcsa.core.subscriptions import update_stripe_subscription
from .models import Payment, update_cart_items, Recipe

User = get_user_model()

TWOPLACES = Decimal(10) ** -2


def export_as_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="ffcsa_order_export.csv"'

    writer = csv.writer(response)
    writer.writerow(
        ['Order Date', 'Last Name', 'Drop Site', 'Vendor', 'Category', 'Item', 'SKU', 'Member Price',
         'Vendor Price', 'Quantity', 'Member Total Price', 'Vendor Total Price', 'Parent Category Order On Invoice',
         'Child Category Order On Invoice'])

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

            category = Category.objects.filter(description__contains=item.category).first()
            if category:
                add_blank = True
                if category.parent:
                    row.append(category.parent.category.order_on_invoice)
                    add_blank = False

                row.append(category.order_on_invoice)
                if add_blank:
                    row.append('')

            writer.writerow(row)

    return response


export_as_csv.short_description = "Export As CSV"

DEFAULT_GROUP_KEY = 0


def keySort(categories):
    def func(item):
        try:
            cat = categories.get(titles=item.category)

            if not cat.parent:
                return (cat.order_on_invoice, item.description)

            if cat.parent and cat.parent.category:
                parent_order = cat.parent.category.order_on_invoice
                order = cat.order_on_invoice
                if order == 0:
                    order = DEFAULT_GROUP_KEY

                return (
                    float("{}.{}".format(parent_order, order)),
                    item.description
                )

        except Category.DoesNotExist:
            pass

        # just return a default number for category
        return (DEFAULT_GROUP_KEY, item.description)

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
        context['details'] = [
            [("Name", order.billing_detail_first_name + " " + order.billing_detail_last_name)],
            [("Phone", order.billing_detail_phone), ("Alt. Phone", order.billing_detail_phone_2)],
        ]

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
productvariation_fields.insert(2, "weekly_inventory")
productvariation_fields.insert(3, "vendor_price")


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


accounts_base.ProfileInline.readonly_fields = ['payment_method', 'ach_status', 'google_person_id']
accounts_base.ProfileInline.fieldsets = (
    (None, {'fields': ('phone_number', 'phone_number_2', 'notes', 'invoice_notes')}),
    ('Payments', {'fields': (
        'monthly_contribution', 'discount_code', 'paid_signup_fee', 'payment_agreement', 'payment_method', 'ach_status',
        'stripe_subscription_id', 'stripe_customer_id')}),
    ('Preferences', {'fields': ('drop_site', 'no_plastic_bags', 'allow_substitutions', 'weekly_emails')}),
    ('Other', {'fields': ('start_date', 'can_order', 'product_agreement', 'non_subscribing_member')}),

)

user_fieldsets = deepcopy(accounts_base.UserProfileAdmin.fieldsets)
user_fieldsets[2][1]['classes'] = ('collapse', 'collapse-closed')
SitePermissionInline.classes = ('collapse', 'collapse-closed')


class UserProfileAdmin(accounts_base.UserProfileAdmin):
    fieldsets = user_fieldsets

    def save_model(self, request, obj, form, change):
        """
        Update stripe subscription if needed
        """
        user = User.objects.get(id=obj.id)
        if change \
                and user.profile.monthly_contribution != obj.profile.monthly_contribution \
                and obj.profile.stripe_subscription_id:
            update_stripe_subscription(obj)
        if change and obj.profile.non_subscribing_member:
            if user.profile.stripe_subscription_id:
                # TODO: this is not a very good UX
                self.message_user(request, 'Non-subscribing members can not have an existing subscription',
                                  messages.ERROR)
                raise ValidationError('Non-subscribing members can not have an existing subscription')
            # create stripe user if not already existing
            if not obj.profile.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=user.email,
                    description=user.get_full_name()
                )
                obj.profile.stripe_customer_id = customer.id

            # only accepts CC payments
            obj.profile.payment_method = 'CC'
            obj.profile.ach_status = None

        super(UserProfileAdmin, self).save_model(request, obj, form, change)


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
        updating = obj.id is not None
        if updating:
            orig = Product.objects.filter(id=obj.id).first()
            orig_sku = orig.sku
        super(ProductAdmin, self).save_model(request, obj, form, change)

        # obj.variations.all()[0].live_num_in_stock()

        # update any cart items if necessary
        if updating and not settings.SHOP_USE_VARIATIONS and 'changelist' in request.resolver_match.url_name:
            # This is called in both the product admin & product admin changelist view
            # Since the product admin doesn't update the Product to include the default
            # variation values until later, we only want to update_cart_items if we are
            # in the changelist view. Otherwise update_cart_items needs to be called
            # in a different method after the Product has been updated. We do this in
            # Product.copy_default_variation
            update_cart_items(obj, orig_sku)

        if "available" in form.changed_data and not obj.available:
            cart_url = request.build_absolute_uri(reverse("shop_cart"))
            inform_user_product_unavailable(obj.sku, obj.title, cart_url)


class PaymentAdmin(admin.ModelAdmin):
    date_hierarchy = 'date'
    list_display = ('user', 'date', 'amount')
    list_filter = ("user", "date")
    search_fields = ["user__first_name", "user__last_name", "user__username"]

    actions = ['bulk_edit']

    def bulk_edit(self, request, queryset):
        selected = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)
        return HttpResponseRedirect(reverse('admin_bulk_payments') + "?ids=%s" % ",".join(selected))

    bulk_edit.short_description = "Edit selected payments"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            kwargs["queryset"] = User.objects.filter(is_active=True).order_by('last_name')
        return super(PaymentAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


recipe_fieldsets = deepcopy(PageAdmin.fieldsets)
recipe_fieldsets[0][1]["fields"][3:3] = ["content"]
# for some reason the trailing , in the classes tuple causes django to throw the error: (admin.E012) There are duplicate field(s) in 'fieldsets[0][1]'.
# so we remove it here
recipe_fieldsets[1][1]['classes'] = ('collapse', 'collapse-closed')
if settings.SHOP_CATEGORY_USE_FEATURED_IMAGE:
    recipe_fieldsets[0][1]["fields"].insert(3, "featured_image")


class RecipeProductInlineAdmin(admin.TabularInline):
    model = Recipe.products.through

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "product":
            kwargs["queryset"] = Product.objects.filter(available=True, status=CONTENT_STATUS_PUBLISHED)
        return super(RecipeProductInlineAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


class RecipeAdmin(PageAdmin):
    form = CategoryAdminForm
    fieldsets = recipe_fieldsets
    formfield_overrides = {ImageField: {"widget": ImageWidget}}
    inlines = (RecipeProductInlineAdmin,)


admin.site.unregister(Order)
admin.site.register(Order, MyOrderAdmin)
admin.site.unregister(Category)
admin.site.register(Category, MyCategoryAdmin)
admin.site.unregister(Product)
admin.site.register(Product, ProductAdmin)
admin.site.unregister(User)
admin.site.register(User, UserProfileAdmin)

admin.site.register(Payment, PaymentAdmin)
admin.site.register(Recipe, RecipeAdmin)

# TODO remove all unnecessary admin menus
admin.site.unregister(ThreadedComment)
admin.site.unregister(Sale)
