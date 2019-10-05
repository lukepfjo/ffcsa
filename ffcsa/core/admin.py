from __future__ import unicode_literals

import csv
import tempfile
import zipfile
import collections
from functools import partial

import labels
import stripe
from itertools import groupby

from decimal import Decimal

from copy import deepcopy

from cachetools import cached
from cartridge.shop.forms import ImageWidget
from dal import autocomplete
from django.contrib.messages import info
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.db.models import F, ImageField
from django import forms
from django.forms import modelformset_factory, inlineformset_factory
from django.http import HttpResponse, HttpResponseRedirect
from django.template.loader import get_template
from django.template.response import TemplateResponse
from django.urls import reverse

from cartridge.shop.models import Category, Product, Order, Sale, ProductVariation, DiscountCode
from django.contrib import admin

from cartridge.shop import admin as base
from mezzanine.accounts import admin as accounts_base

from mezzanine.conf import settings
from mezzanine.core.admin import SitePermissionInline
from mezzanine.generic.models import ThreadedComment
from mezzanine.pages.admin import PageAdmin
from mezzanine.utils.static import static_lazy as static
from reportlab.graphics import shapes
from reportlab.pdfbase.pdfmetrics import stringWidth
from weasyprint import HTML

from ffcsa.core.availability import inform_user_product_unavailable
from ffcsa.core.forms import CategoryAdminForm, OrderAdminForm
from ffcsa.core.subscriptions import update_stripe_subscription
from .models import Payment, update_cart_items, Recipe, RecipeProduct

User = get_user_model()

TWOPLACES = Decimal(10) ** -2


def draw_label(label, width, height, order):
    last_name = order.billing_detail_last_name
    first_name = order.billing_detail_first_name
    drop_site = order.drop_site

    color = settings.DROP_SITE_COLORS[drop_site] if drop_site in settings.DROP_SITE_COLORS else 'grey'
    strokeColor = color if color is not 'white' else 'black'
    label.add(shapes.Circle(17, 17, 12, fillColor=color, strokeColor=strokeColor))

    # Write the dropsite.
    label.add(shapes.String(width - 8, 10, drop_site, fontSize=16, textAnchor='end'))

    # Measure the width of the name and shrink the font size until it fits.
    font_size = 20
    text_width = width - 16
    name = "{}, {}".format(last_name, first_name)
    name_width = stringWidth(name, "Helvetica", font_size)
    while name_width > text_width:
        font_size *= 0.8
        name_width = stringWidth(name, "Helvetica", font_size)

    # Write out the name in the centre of the label with a random colour.
    # s = shapes.String(width / 2.0, height - 30, name, textAnchor="middle")
    s = shapes.String(8, height - 30, name)
    s.fontName = "Helvetica"
    s.fontSize = font_size
    # s.fillColor = random.choice((colors.black, colors.blue, colors.red, colors.green))
    label.add(s)


class SkipLabelsForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    skip = forms.IntegerField(max_value=30)


def order_sort(order):
    if order.drop_site in settings.DROP_SITE_ORDER:
        return (settings.DROP_SITE_ORDER.index(order.drop_site), order.billing_detail_last_name)
    return (len(settings.DROP_SITE_ORDER), order.billing_detail_last_name)


def create_labels(modeladmin, request, queryset):
    if 'cancel' in request.POST:
        info(request, 'Canceled label creation.')
        return
    if 'create' in request.POST:
        form = SkipLabelsForm(request.POST)

        if form.is_valid():
            # Create an A4 portrait (210mm x 297mm) sheets with 2 columns and 8 rows of
            # labels. Each label is 90mm x 25mm with a 2mm rounded corner. The margins are
            # automatically calculated.
            # These settings are configured for Avery 5160 Address Labels
            specs = labels.Specification(217, 279, 3.25, 10, 70, 26.6, corner_radius=2, row_gap=0, column_gap=3,
                                         top_margin=8.25, left_margin=.8)

            sheet = labels.Sheet(specs, draw_label)

            to_skip = form.cleaned_data['skip']
            if to_skip > 0:
                used = []
                row = 1
                col = 1
                for i in range(1, to_skip + 1):
                    used.append((row, col))
                    # label sheet has 3 columns
                    if i % 3 == 0:
                        row += 1
                        col = 1
                    else:
                        col += 1

                sheet.partial_page(1, used)

            orders = [o for o in queryset]
            orders.sort(key=order_sort)
            for order in orders:
                sheet.add_label(order)

            with tempfile.NamedTemporaryFile() as tmp:
                sheet.save(tmp)

                # Reset file pointer
                tmp.seek(0)

                # Write file data to response
                response = HttpResponse(tmp.read(), content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="ffcsa_order_labels.pdf"'
                return response
    else:
        form = SkipLabelsForm(initial={'skip': 0, '_selected_action': request.POST.getlist(admin.ACTION_CHECKBOX_NAME)})

    return TemplateResponse(request, 'admin/skip_labels.html', {'form': form})


create_labels.short_description = "Create Box Labels"


def export_as_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="ffcsa_order_export.csv"'

    writer = csv.writer(response)
    writer.writerow(
        ['Order Date', 'Last Name', 'Drop Site', 'Vendor', 'Category', 'Item', 'SKU', 'Member Price',
         'Vendor Price', 'Quantity', 'Member Total Price', 'Vendor Total Price', 'Parent Category Order On Invoice',
         'Child Category Order On Invoice', 'Allow Substitutions'])

    products = Product.objects.all()
    product_cache = {}
    for order in queryset:
        last_name = order.billing_detail_last_name
        drop_site = order.drop_site
        row_base = [order.time.date(), last_name, drop_site]

        for item in order.items.all():
            product = product_cache[item.sku] if item.sku in product_cache else products.filter(
                sku=item.sku).first()
            if not product:
                product = products.filter(title=item.description).first()
            if product:
                if not product.sku in product_cache:
                    product_cache[product.sku] = product
                if not item.vendor:
                    item.vendor = product.vendor
                if not item.category:
                    item.category = str(product.get_category())
                if not item.vendor_price:
                    item.vendor_price = product.vendor_price
            row = row_base.copy()
            vendor = item.vendor
            if not vendor and product:
                vendor = product.vendor
            row.append(vendor)
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

            if product and product.order_on_invoice:
                parts = str(product.order_on_invoice).split('.')
                row.append(parts[0])
                row.append(parts[1] if len(parts) == 2 else '')
            else:
                category = product.get_category() if product else Category.objects.filter(
                    description__contains=item.category).first()
                if category:
                    add_blank = True
                    if category.parent:
                        row.append(category.parent.category.order_on_invoice)
                        add_blank = False

                    row.append(category.order_on_invoice)
                    if add_blank:
                        row.append('')

            row.append('yes' if order.allow_substitutions else 'no')
            writer.writerow(row)

    return response


export_as_csv.short_description = "Export As CSV"

DEFAULT_GROUP_KEY = 5


def keySort(categories):
    def func(item):
        try:
            product = Product.objects.get(title=item.description, sku=item.sku)
            if product and product.order_on_invoice:
                return (product.order_on_invoice, item.description)
        except Product.DoesNotExist:
            pass

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

    orders = [o for o in queryset]
    orders.sort(key=order_sort)
    for order in orders:
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
        prefix = settings.DROP_SITE_ORDER.index(
            order.drop_site) if order.drop_site in settings.DROP_SITE_ORDER else len(settings.DROP_SITE_ORDER)
        invoices["{}_{}_{}_{}".format(prefix, order.drop_site, order.billing_detail_last_name, order.id)] = invoice
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
    actions = [export_as_csv, download_invoices, create_labels]
    fieldsets = order_admin_fieldsets
    form = OrderAdminForm

    # class Media:
    #     js = (static("js/admin/orders.js"),)

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

        form.instance.item_total = total

        if form.instance.discount_code:
            try:
                dc = DiscountCode.objects.get(code=form.instance.discount_code)
                form.instance.discount_total = dc.calculate(total)
                form.instance.total = total - form.instance.discount_total
            except DiscountCode.DoesNotExist:
                form.instance.total = total - form.instance.discount_total
        else:
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


base.ProductAdmin.fieldsets[0][1]['fields'].append('order_on_invoice')

product_list_display = deepcopy(base.ProductAdmin.list_display)
# remove sku, sale_price
product_list_display.pop(2)
product_list_display.pop(3)
product_list_display.pop(4)
product_list_display.insert(3, "vendor_price")
product_list_display.insert(5, 'weekly_inventory')
product_list_display.insert(7, 'vendor')
product_list_display.insert(8, 'order_on_invoice')
# product_list_display.insert(9, 'cat')

product_list_editable = base.ProductAdmin.list_editable
# remove status, sku, sale_price
product_list_editable.pop(0)
product_list_editable.pop(1)
product_list_editable.pop(2)
product_list_editable.append("vendor_price")
product_list_editable.append("weekly_inventory")
product_list_editable.append("order_on_invoice")

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


def get_variation_field(obj, field):
    if obj.variations.count() > 1:
        return None

    return str(getattr(obj.variations.first(), field, ''))


class ProductChangelistForm(forms.ModelForm):
    vendor = forms.CharField()

    class Meta:
        model = Product
        fields = ('vendor',)

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        if instance:
            initial = kwargs.get('initial', {})
            initial['vendor'] = getattr(instance, 'vendor')
            kwargs['initial'] = initial
        super(ProductChangelistForm, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        obj = super(ProductChangelistForm, self).save(*args, **kwargs)
        if obj.variations.count() == 1:
            variation = obj.variations.first()
            variation.vendor = self.cleaned_data['vendor']
            variation.save()

        return obj


class ProductAdmin(base.ProductAdmin):
    actions = [export_price_list]
    inlines = (base.ProductImageAdmin, ProductVariationAdmin)
    list_display = product_list_display
    list_editable = product_list_editable
    list_filter = product_list_filter

    def get_changelist_form(self, request, **kwargs):
        return ProductChangelistForm

    def cat(self, obj):
        return 'Multiple' if obj.categories.count() > 1 else obj.get_category()

    cat.short_description = 'Category'

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


class ProductForm(forms.ModelForm):
    class Meta:
        model = RecipeProduct
        fields = ('__all__')
        widgets = {
            'product': autocomplete.ModelSelect2(url='product-autocomplete')
        }


class RecipeProductInlineAdmin(admin.TabularInline):
    model = Recipe.products.through
    form = ProductForm


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
