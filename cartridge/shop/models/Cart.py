from collections import OrderedDict
from decimal import Decimal
from itertools import takewhile

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from future.builtins import super
from mezzanine.conf import settings

from cartridge.shop import managers
from cartridge.shop.models.Order import Order
from ffcsa.core.models import Payment


class Cart(models.Model):
    last_updated = models.DateTimeField(_("Last updated"), null=True)

    # TODO change to fk?
    user_id = models.IntegerField(blank=False, null=False, unique=True)
    attending_dinner = models.IntegerField(blank=False, null=False, default=0)

    objects = managers.PersistentCartManager()

    def __iter__(self):
        """
        Allow the cart to be iterated giving access to the cart's items,
        ensuring the items are only retrieved once and cached.
        """
        if not hasattr(self, "_cached_items"):
            self._cached_items = self.items.all()
        return iter(self._cached_items)

    def add_item(self, variation, quantity):
        """
        Increase quantity of existing item if variation matches, otherwise create new.
        """
        if not self.user_id:
            raise Exception("You must be logged in to add products to your cart")
        if not self.pk:
            self.save()
        item, created = self.items.get_or_create(variation=variation)
        if created:
            variation.product.actions.added_to_cart()

        item.update_quantity(quantity)
        item.save()

    def clear(self):
        self.attending_dinner = 0
        self.items.all().delete()

    def over_budget(self, additional_total=0):
        return self.remaining_budget() < additional_total

    def remaining_budget(self):
        if not self.user_id:
            return 0

        User = get_user_model()
        user = User.objects.get(pk=self.user_id)

        ytd_order_total = Order.objects.total_for_user(user)
        ytd_payment_total = Payment.objects.total_for_user(user)

        return ytd_payment_total - (ytd_order_total + self.total_price_after_discount())

    def discount(self):
        if not self.user_id:
            return 0

        User = get_user_model()
        user = User.objects.get(pk=self.user_id)

        if not user or not user.profile.discount_code:
            return 0

        return self.calculate_discount(user.profile.discount_code)

    def total_price_after_discount(self):
        return self.total_price() - self.discount()

    def has_items(self):
        """
        Template helper function - does the cart have items?
        """
        return len(list(self)) > 0

    def total_quantity(self):
        """
        Template helper function - sum of all item quantities.
        """
        return sum([item.quantity for item in self])

    def total_price(self):
        """
        Template helper function - sum of all costs of item quantities.
        """
        return sum([item.total_price for item in self])

    def skus(self):
        """
        Returns a list of skus for items in the cart. Used by
        ``upsell_products`` and ``calculate_discount``.
        """
        return [item.sku for item in self]

    def upsell_products(self):
        """
        Returns the upsell products for each of the items in the cart.
        """
        from cartridge.shop.models import Product
        if not settings.SHOP_USE_UPSELL_PRODUCTS:
            return []
        cart = Product.objects.filter(variations__sku__in=self.skus())
        published_products = Product.objects.published()
        for_cart = published_products.filter(upsell_products__in=cart)
        with_cart_excluded = for_cart.exclude(variations__sku__in=self.skus())
        return list(with_cart_excluded.distinct())

    def calculate_discount(self, discount):
        """
        Calculates the discount based on the items in a cart, some
        might have the discount, others might not.
        """
        from cartridge.shop.models import ProductVariation
        # Discount applies to cart total if not product specific.
        products = discount.all_products()
        if products.count() == 0:
            return discount.calculate(self.total_price())
        total = Decimal("0")
        # Create a list of skus in the cart that are applicable to
        # the discount, and total the discount for appllicable items.
        lookup = {"product__in": products, "sku__in": self.skus()}
        discount_variations = ProductVariation.objects.filter(**lookup)
        discount_skus = discount_variations.values_list("sku", flat=True)
        for item in self:
            if item.sku in discount_skus:
                total += discount.calculate(item.unit_price) * item.quantity
        return total


class CartItem(models.Model):
    cart = models.ForeignKey("shop.Cart", related_name="items", on_delete=models.CASCADE)
    variation = models.ForeignKey("shop.ProductVariation", related_name="+", on_delete=models.PROTECT, null=False)
    time = models.DateTimeField(_("Time"), auto_now_add=True, null=True)

    objects = managers.CartItemManager()

    def __str__(self):
        return ''

    @property
    def image(self):
        return self.variation.image

    @property
    def description(self):
        return force_text(self.variation)

    @property
    def unit_price(self):
        return self.variation.price()

    @property
    def category(self):
        return self.variation.product.get_category()

    @property
    def vendor_price(self):
        return self.variation.vendor_price

    @property
    def in_inventory(self):
        return self.variation.product.in_inventory

    @property
    def is_frozen(self):
        return self.variation.product.is_frozen

    @property
    def sku(self):
        return self.variation.sku

    @property
    def total_price(self):
        return self.unit_price * self.quantity

    def get_absolute_url(self):
        return self.variation.product.get_absolute_url()

    @property
    def quantity(self):
        # The following check works in Django 2.2
        # if 'vendorproductvariation_set' not in self._state.fields_cache:
        if not hasattr(self, "_cached_quantity"):
            if 'vendors' not in getattr(self, '_prefetched_objects_cache', []) \
                    and not hasattr(self, self._meta.get_field('vendors').get_cache_name()):
                quantity = self.vendors.aggregate(quantity=models.Sum("quantity"))['quantity']
            else:
                quantity = sum([v.quantity for v in self.vendors.all()])
            self._cached_quantity = quantity
        return self._cached_quantity

    def update_quantity(self, quantity):
        vendor_items = []
        diff = quantity - (self.quantity if self.quantity is not None else 0)

        if diff == 0:
            return

        if diff > 0:
            remaining = diff
            qs = self.variation.vendorproductvariation_set.all().order_by('_order')
            for vpv in takewhile(lambda x: remaining > 0, qs):
                stock = vpv.live_num_in_stock()
                # If stock is None then there is no limit.
                qty = min(stock, remaining) if stock is not None else remaining
                vi, created = self.vendors.get_or_create(vendor_id=vpv.vendor_id)
                vi._order = vpv._order
                vi.quantity = vi.quantity + qty
                vendor_items.append(vi)
                remaining = remaining - qty
        else:
            remaining = abs(diff)
            qs = self.vendors.all().order_by('-_order')
            for v in takewhile(lambda x: remaining > 0, qs):
                # Product vendors are listed by preference using the _order field
                # So we want to decrease quantity starting from least preferred vendors
                qty = min(remaining, v.quantity)
                v.quantity = v.quantity - qty
                vendor_items.append(v)
                remaining = remaining - qty

        for item in vendor_items:
            if item.quantity < 0:
                raise AssertionError('Item quantity is negative')
            item.delete() if item.quantity == 0 else item.save()

        if hasattr(self, '_cached_quantity') and self._cached_quantity is not None:
            self._cached_quantity = quantity

    def save(self, *args, **kwargs):
        super(CartItem, self).save(*args, **kwargs)

        # Check if this is the last cart item being removed
        if self.quantity == 0 and not self.cart.items.exists():
            self.cart.delete()


def update_cart_items(variation):
    """
    When an item has changed, update any items that are already in the cart
    """
    from ffcsa.core.budgets import clear_cached_budget_for_user_id
    carts = Cart.objects.filter(items__variation__sku=variation.sku)
    for cart in carts:
        clear_cached_budget_for_user_id(cart.user_id)
