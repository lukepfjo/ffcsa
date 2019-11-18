from django.db import connection, models
from django.db.models import F
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _
from future.builtins import super
from mezzanine.conf import settings

from ffcsa.shop.models import Product, ProductVariation
from ffcsa.shop.models.Discount import Discount


class Sale(Discount):
    """
    Stores sales field values for price and date range which when saved
    are then applied across products and variations according to the
    selected categories and products for the sale.
    """

    class Meta:
        verbose_name = _("Sale")
        verbose_name_plural = _("Sales")

    def save(self, *args, **kwargs):
        super(Sale, self).save(*args, **kwargs)
        self.update_products()

    def update_products(self):
        """
        Apply sales field value to products and variations according
        to the selected categories and products for the sale.
        """
        self._clear()
        if self.active:
            extra_filter = {}
            if self.discount_deduct is not None:
                # Don't apply to prices that would be negative
                # after deduction.
                extra_filter["unit_price__gt"] = self.discount_deduct
                sale_price = models.F("unit_price") - self.discount_deduct
            elif self.discount_percent is not None:
                sale_price = models.F("unit_price") - (
                    F("unit_price") / "100.0" * self.discount_percent)
            elif self.discount_exact is not None:
                # Don't apply to prices that are cheaper than the sale
                # amount.
                extra_filter["unit_price__gt"] = self.discount_exact
                sale_price = self.discount_exact
            else:
                return
            products = self.all_products()
            variations = ProductVariation.objects.filter(product__in=products)
            for priced_objects in (products, variations):
                update = {"sale_id": self.id,
                          "sale_price": sale_price,
                          "sale_to": self.valid_to,
                          "sale_from": self.valid_from}
                using = priced_objects.db
                if "mysql" not in settings.DATABASES[using]["ENGINE"]:
                    priced_objects.filter(**extra_filter).update(**update)
                else:
                    # Work around for MySQL which does not allow update
                    # to operate on subquery where the FROM clause would
                    # have it operate on the same table, so we update
                    # each instance individually: http://bit.ly/1xMOGpU
                    #
                    # Also MySQL may raise a 'Data truncated' warning here
                    # when doing a calculation that exceeds the precision
                    # of the price column. In this case it's safe to ignore
                    # it and the calculation will still be applied, but
                    # we need to massage transaction management in order
                    # to continue successfully: http://bit.ly/1xMOJCd
                    for priced in priced_objects.filter(**extra_filter):
                        for field, value in list(update.items()):
                            setattr(priced, field, value)
                        try:
                            priced.save()
                        except Warning:
                            connection.set_rollback(False)

    def delete(self, *args, **kwargs):
        """
        Clear this sale from products when deleting the sale.
        """
        self._clear()
        super(Sale, self).delete(*args, **kwargs)

    def _clear(self):
        """
        Clears previously applied sale field values from products prior
        to updating the sale, when deactivating it or deleting it.
        """
        update = {"sale_id": None, "sale_price": None,
                  "sale_from": None, "sale_to": None}
        for priced_model in (Product, ProductVariation):
            priced_model.objects.filter(sale_id=self.id).update(**update)


@receiver(m2m_changed, sender=Sale.products.through)
def sale_update_products(sender, instance, action, *args, **kwargs):
    """
    Signal for updating products for the sale - needed since the
    products won't be assigned to the sale when it is first saved.
    """
    if action == "post_add":
        instance.update_products()
