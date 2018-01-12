import datetime

from cartridge.shop.fields import MoneyField
from cartridge.shop.models import Cart, Product
from copy import deepcopy

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.db import models

from .utils import get_ytd_order_total, get_ytd_payment_total
from ffcsa.core import managers

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

    if should_save:
        item.save()


Cart.add_item = cart_add_item


# extend the Cart model
class CartExtend:
    def clear(self):
        self.attending_dinner = 0
        self.items.all().delete()

    def over_budget(self, additional_total=0):
        User = get_user_model()
        user = User.objects.get(pk=self.user_id)

        ytd_order_total = get_ytd_order_total(user)
        ytd_payment_total = get_ytd_payment_total(user)

        return ytd_payment_total < (ytd_order_total + additional_total + self.total_price())


Cart.__bases__ += (CartExtend,)

PHONE_REGEX = RegexValidator(regex=r'^\+?(1-)?\d{3}-\d{3}-\d{4}$',
                             message="Phone number must be entered in the format: '999-999-9999'.")


class Profile(models.Model):
    user = models.OneToOneField("auth.User")
    monthly_contribution = MoneyField("Default Monthly Contribution", decimal_places=0)
    phone_number = models.CharField("Contact Number", validators=[PHONE_REGEX], blank=True, max_length=15)
    phone_number_2 = models.CharField("Alternate Contact Number", validators=[PHONE_REGEX], blank=True, max_length=15)
    drop_site = models.CharField("Drop Site", blank=True, max_length=255)
    start_date = models.DateField("CSA Start Date", blank=True, null=True)

    def csa_year_start_date(self):
        """
        member start_date for the current csa year
        """
        ONE_YEAR = 365
        today = datetime.date.today()
        start_date = self.start_date if self.start_date else self.user.date_joined.date()

        while (today - start_date).days > ONE_YEAR:
            start_date = start_date + datetime.timedelta(days=ONE_YEAR)

        return start_date

    def csa_months_ytd(self):
        """
         number of months since the start of the user's csa year

         using the users join_date, no later then 1 year ago, return the number of months since then
        """
        month = self.csa_year_start_date().month
        today = datetime.date.today()

        if today.month > month:
            return today.month - month

        return today.month - month + 12


class Payment(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    date = models.DateField('Payment Date', default=datetime.date.today)
    amount = models.DecimalField('Amount', max_digits=10, decimal_places=2)

    def __str__(self):
        return "%s, %s - %s - $%s" % (self.user.last_name, self.user.first_name, self.date, self.amount)
