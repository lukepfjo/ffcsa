from __future__ import division, unicode_literals

from django.db import models

from cartridge.shop import managers


class ProductAction(models.Model):
    """
    Records an incremental value for an action against a product such
    as adding to cart or purchasing, for sales reporting and
    calculating popularity. Not yet used but will be used for product
    popularity and sales reporting.
    """

    product = models.ForeignKey("shop.Product", related_name="actions",
                                on_delete=models.CASCADE)
    timestamp = models.IntegerField()
    total_cart = models.IntegerField(default=0)
    total_purchase = models.IntegerField(default=0)

    objects = managers.ProductActionManager()

    class Meta:
        unique_together = ("product", "timestamp")
