from _pydecimal import Decimal

from django.db import models
from django.utils.translation import ugettext_lazy as _

from cartridge.shop import fields, managers
from cartridge.shop.models.Discount import Discount


class DiscountCode(Discount):
    """
    A code that can be entered at the checkout process to have a
    discount applied to the total purchase amount.
    """

    code = fields.DiscountCodeField(_("Code"), unique=True)
    min_purchase = fields.MoneyField(_("Minimum total purchase"))
    free_shipping = models.BooleanField(_("Free shipping"), default=False)
    uses_remaining = models.IntegerField(_("Uses remaining"), blank=True,
                                         null=True, help_text=_("If you wish to limit the number of times a "
                                                                "code may be used, set this value. It will be decremented upon "
                                                                "each use."))

    objects = managers.DiscountCodeManager()

    def calculate(self, amount):
        """
        Calculates the discount for the given amount.
        """
        if self.discount_deduct is not None:
            # Don't apply to amounts that would be negative after
            # deduction.
            if self.discount_deduct <= amount:
                return self.discount_deduct
        elif self.discount_percent is not None:
            return amount / Decimal("100") * self.discount_percent
        return 0

    class Meta:
        verbose_name = _("Discount code")
        verbose_name_plural = _("Discount codes")
