import datetime

from cartridge.shop.fields import MoneyField
from cartridge.shop.models import Cart, Product, ProductVariation, Priced
from copy import deepcopy

from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.db import models
from django import forms
from django.utils.safestring import mark_safe
from mezzanine.core.fields import RichTextField

from .utils import get_order_total, get_payment_total
from ffcsa.core import managers

###################
#  CART
###################

# Replace CartManager with our PersistentCartManger
cart_manager = managers.PersistentCartManager()
# need to call this, as django does some setup for the managers that wouldn't happen if we just monkey patch the manager
Cart.add_to_class('objects', cart_manager)
Cart.objects = cart_manager

# monkey patch the cart add item to use custom add_item method
original_cart_add_item = deepcopy(Cart.add_item)


def cart_add_item(self, *args, **kwargs):
    if not self.user_id:
        raise Exception("You must be logged in to add products to your cart")

    original_cart_add_item(self, *args, **kwargs)

    # a bit hacky as this performs multiple saves, but add the category and vendor to the CartItem object
    kwargs = {"sku": args[0].sku, "unit_price": args[0].price()}
    item = self.items.get(**kwargs)

    should_save = False

    if not item.category:
        p = Product.objects.filter(sku=item.sku).first()
        item.category = ",".join([c.titles for c in p.categories.exclude(slug='weekly-box')])
        should_save = True
    if not item.vendor:
        item.vendor = args[0].vendor
        should_save = True
    if not item.vendor_price:
        item.vendor_price = args[0].vendor_price
        should_save = True
    if args[0].weekly_inventory != item.weekly_inventory:
        item.weekly_inventory = args[0].weekly_inventory
        should_save = True

    if should_save:
        item.save()


Cart.add_item = cart_add_item


# extend the Cart model
class CartExtend:
    def clear(self):
        self.attending_dinner = 0
        self.items.all().delete()

    def over_budget(self, additional_total=0):
        return self.remaining_budget() < additional_total

    def remaining_budget(self):
        User = get_user_model()
        user = User.objects.get(pk=self.user_id)

        ytd_order_total = get_order_total(user)
        ytd_payment_total = get_payment_total(user)

        return ytd_payment_total - (ytd_order_total + self.total_price())


Cart.__bases__ += (CartExtend,)

###################
#  Priced
###################

# monkey patch the Priced copy_price_fields_to to also copy vendor_price
original_copy_price_fields_to = deepcopy(Priced.copy_price_fields_to)


def copy_price_fields_to(self, obj_to):
    original_copy_price_fields_to(self, obj_to)
    setattr(obj_to, "vendor_price", getattr(self, "vendor_price"))
    obj_to.save()


Priced.copy_price_fields_to = copy_price_fields_to

# rename unit price to member price
Product._meta.get_field("unit_price").verbose_name = "Member Price"
ProductVariation._meta.get_field("unit_price").verbose_name = "Member Price"


###################
#  Product
###################

# monkey patch the get_category
def product_get_category(self):
    """
    Returns the single category this product is associated with, or None
    if the number of categories is not exactly 1. We exclude the weekly
    example box category from this
    """
    categories = self.categories.exclude(slug='weekly-box')
    if len(categories) == 1:
        return categories[0]
    return None


Product.get_category = product_get_category

###################
#  User
###################

User = get_user_model()


def patched_str_(self):
    if self.last_name and self.first_name:
        return "{}, {}".format(self.last_name, self.first_name)

    return self.get_username()


User.__str__ = patched_str_

###################
#  Profile
###################


PHONE_REGEX = RegexValidator(regex=r'^\+?(1-)?\d{3}-\d{3}-\d{4}$',
                             message="Phone number must be entered in the format: '999-999-9999'.")


class Profile(models.Model):
    user = models.OneToOneField("auth.User")
    monthly_contribution = MoneyField("Monthly Contribution", decimal_places=2)
    phone_number = models.CharField("Contact Number", validators=[PHONE_REGEX], max_length=15)
    phone_number_2 = models.CharField("Alternate Contact Number", validators=[PHONE_REGEX], blank=True, max_length=15)
    drop_site = models.CharField("Drop Site", blank=True, max_length=255)
    notes = RichTextField("Customer Notes", blank=True)
    invoice_notes = models.TextField("Invoice Notes", blank=True,
                                     help_text="Use &lt;br/&gt; to enter a newline, and &lt;b&gt;My Text&lt;/b&gt; to make something bold.")
    start_date = models.DateField("CSA Start Date", blank=True, null=True)
    stripe_customer_id = models.CharField(blank=True, null=True, max_length=255)
    stripe_subscription_id = models.CharField(blank=True, null=True, max_length=255)
    payment_method = models.CharField(blank=False, null=True,
                                      choices=[('CC', 'Credit Card'), ('ACH', 'Bank Account'), ('CRYPTO', 'Crypto')],
                                      max_length=255)
    ach_status = models.CharField(blank=False, null=True, max_length=20,
                                  choices=[('NEW', 'Unverified'), ('VERIFYING', 'Verifying'), ('VERIFIED', 'Verified'),
                                           ('FAILED', 'Verification Failed')])
    paid_signup_fee = models.BooleanField(default=False)
    can_order = models.BooleanField("Has had dairy conversation", default=False)
    payment_agreement = models.BooleanField(
        "I agree to make monthly payments in order to maintain my membership with the FFCSA for 12 months, with a minimium of $260 per month. If I need to change my monthly payment amount, I will notify the FFCSA admin and keep changes to a maximum of two times per year.",
        default=False)
    product_agreement = models.FileField("Liability Agreement Form",
                                         upload_to='uploads/member_docs/',
                                         blank=True,
                                         help_text=mark_safe(
                                             "Please <a target='_blank' href='/static/docs/Product Liability Agreement.pdf'>download this form</a> and have all adult members in your household sign. Then upload here."))
    non_subscribing_member = models.BooleanField(default=False,
                                                 help_text="Non-subscribing members are allowed to make payments to their ffcsa account w/o having a monthly subscription")

    @property
    def joined_before_dec_2017(self):
        # use early nov b/c dec payments are received in nov
        return self.user.date_joined.date() <= datetime.date(2017, 11, 5)


###################
#  Payment
###################


class Payment(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    date = models.DateField('Payment Date', default=datetime.date.today)
    amount = models.DecimalField('Amount', max_digits=10, decimal_places=2)
    pending = models.BooleanField('Pending', default=False)
    notes = models.TextField('Notes', null=True, blank=True)

    def __str__(self):
        return "%s, %s - %s - $%s" % (self.user.last_name, self.user.first_name, self.date, self.amount)
