from decimal import Decimal

from django.db import models
from django.db.models import CharField
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from future.builtins import super

from cartridge.shop import fields


@python_2_unicode_compatible
class SelectedProduct(models.Model):
    """
    Abstract model representing a "selected" product in a cart or order.
    """

    sku = fields.SKUField()
    description = CharField(_("Description"), max_length=2000)
    quantity = models.IntegerField(_("Quantity"), default=0)
    unit_price = fields.MoneyField(_("Unit price"), default=Decimal("0"))
    total_price = fields.MoneyField(_("Total price"), default=Decimal("0"))

    category = models.TextField(blank=True)
    vendor = models.CharField(blank=True, max_length=255)
    vendor_price = fields.MoneyField(_("Vendor price"), blank=True, null=True)
    in_inventory = models.BooleanField(
        _("FFCSA Inventory"), default=False, blank=False, null=False)

    class Meta:
        abstract = True

    def __str__(self):
        return ""

    def save(self, *args, **kwargs):
        """
        Set the total price based on the given quantity. If the
        quantity is zero, which may occur via the cart page, just
        delete it.
        """
        if not self.id or self.quantity > 0:
            self.total_price = self.unit_price * self.quantity
            super(SelectedProduct, self).save(*args, **kwargs)
        else:
            self.delete()
