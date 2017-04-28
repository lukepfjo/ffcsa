from cartridge.shop.fields import MoneyField
from cartridge.shop.models import Cart
from copy import deepcopy

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


Cart.add_item = cart_add_item


# extend the Cart model
class CartExtend:
    def clear(self):
        self.submitted = False
        self.items.all().delete()


Cart.__bases__ += (CartExtend,)


class Profile(models.Model):
    user = models.OneToOneField("auth.User")
    weekly_budget = MoneyField("Weekly Budget", decimal_places=0)
