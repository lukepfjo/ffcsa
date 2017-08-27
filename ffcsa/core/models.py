import datetime

from cartridge.shop.fields import MoneyField
from cartridge.shop.models import Cart, Product
from copy import deepcopy

from django.core.validators import RegexValidator
from django.db import models

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


Cart.__bases__ += (CartExtend,)

PHONE_REGEX = RegexValidator(regex=r'^\+?(1-)?\d{3}-\d{3}-\d{4}$',
                             message="Phone number must be entered in the format: '999-999-9999'.")


class Profile(models.Model):
    user = models.OneToOneField("auth.User")
    weekly_budget = MoneyField("Weekly Budget", decimal_places=0)
    phone_number = models.CharField("Contact Number", validators=[PHONE_REGEX], blank=True, max_length=15)
    drop_site = models.CharField("Drop Site", blank=True, max_length=255)
    start_date = models.DateField("CSA Start Date", blank=True, null=True)

    def csa_months_ytd(self):
        """
         number of months since the start of the user's csa year

         using the users join_date, no later then 1 year ago, return the number of months since then
        """

        if not self.start_date:
            month = self.user.date_joined.month if self.user.date_joined.month <= 15 else self.user.date_joined.month + 1
        else:
            month = self.start_date.month

        today = datetime.date.today()

        if today.month > month:
            return today.month - month

        return today.month - month + 12
