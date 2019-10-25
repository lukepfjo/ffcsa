from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import CharField, F
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from future.builtins import str, super
from mezzanine.conf import settings

from cartridge.shop import managers
from cartridge.shop.models.SelectedProduct import SelectedProduct
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
        Increase quantity of existing item if SKU matches, otherwise create
        new.
        """
        if not self.user_id:
            raise Exception(
                "You must be logged in to add products to your cart")
        if not self.pk:
            self.save()
        kwargs = {"sku": variation.sku, "unit_price": variation.price()}
        item, created = self.items.get_or_create(**kwargs)
        if created:
            item.description = force_text(variation)
            item.unit_price = variation.price()
            item.url = variation.product.get_absolute_url()
            image = variation.image
            if image is not None:
                item.image = force_text(image.file)
            variation.product.actions.added_to_cart()
        item.quantity += quantity

        # TODO is there a better way to do this now?
        if not item.category:
            # TODO fix this hack
            from cartridge.shop.models import Product
            p = Product.objects.filter(sku=item.sku).first()
            item.category = str(p.get_category())
        if not item.vendor:
            item.vendor = variation.vendor
        if not item.vendor_price:
            item.vendor_price = variation.vendor_price
        if item.in_inventory != variation.in_inventory:
            item.in_inventory = variation.in_inventory
        if variation.weekly_inventory != item.weekly_inventory:
            item.weekly_inventory = variation.weekly_inventory

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

        ytd_order_total = self.objects.total_for_user(user)
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


class CartItem(SelectedProduct):
    cart = models.ForeignKey("shop.Cart", related_name="items",
                             on_delete=models.CASCADE)
    url = CharField(max_length=2000)
    image = CharField(max_length=200, null=True)
    # TODO is this needed?
    weekly_inventory = models.BooleanField(
        _("Weekly Inventory"), blank=False, default=True)

    def get_absolute_url(self):
        return self.url

    def save(self, *args, **kwargs):
        super(CartItem, self).save(*args, **kwargs)

        # Check if this is the last cart item being removed
        if self.quantity == 0 and not self.cart.items.exists():
            self.cart.delete()


def update_cart_items(product, orig_sku):
    """
    When an item has changed, update any items that are already in the cart
    """
    from ffcsa.core.budgets import clear_cached_budget_for_user_id
    cat = product.get_category()
    update = {
        'sku': product.sku,
        'description': product.title,
        'unit_price': product.price(),
        'total_price': F('quantity') * product.price(),
        'category': cat.__str__(),
        'vendor': product.variations.first().vendor,
        'vendor_price': product.vendor_price,
        'in_inventory': product.in_inventory,
        'weekly_inventory': product.weekly_inventory
    }

    items = CartItem.objects.filter(sku=orig_sku)
    items.update(**update)
    for item in items:
        clear_cached_budget_for_user_id(item.cart.user_id)
        return
