from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models
from django.db.models.base import ModelBase
from django.utils.translation import ugettext_lazy as _
from mezzanine.core.fields import FileField
from mezzanine.core.managers import DisplayableManager
from mezzanine.core.models import Displayable, Orderable, RichText
from mezzanine.utils.models import upload_to

from ffcsa.shop.models import Cart


class Vendor(RichText, Orderable, Displayable):
    expiry_date = None
    featured_image = FileField(verbose_name=_("Featured Image"),
                               upload_to=upload_to(
                                   "shop.Vendor.featured_image", "vendors"),
                               format="Image", max_length=255, null=True, blank=True)
    email = models.EmailField(_("Email"), max_length=254, blank=True, null=True)
    auto_send_order = models.BooleanField(help_text="Automatically email order to vendor?", default=True)

    objects = DisplayableManager()

    class Meta:
        ordering = ('title',)

    def clean(self):
        if self.auto_send_order and not self.email:
            raise ValidationError("You must provide an email address if auto_send_order is True")

    @models.permalink
    def get_absolute_url(self):
        # TODO if in index, return heirarachal url
        # if category:
        #     return ("shop_category_product", (), {
        #         "category_slug": category.get_raw_slug(),
        #         "slug": self.slug})
        return ("shop_vendor", (), {"slug": self.slug})


class VendorProductVariation(models.Model):
    vendor = models.ForeignKey(
        Vendor, verbose_name="Vendor", on_delete=models.CASCADE)
    variation = models.ForeignKey(
        "shop.ProductVariation", verbose_name="variation", on_delete=models.CASCADE)
    num_in_stock = models.IntegerField(_("Number in stock"), blank=True, null=True)

    class Meta:
        verbose_name = _("Vendor Product Variation")
        verbose_name_plural = _("Vendor Product Variations")
        unique_together = ('vendor', 'variation')
        order_with_respect_to = 'variation'

    def __str__(self):
        return '%s: %s' % (self.variation, self.vendor)

    def live_num_in_stock(self):
        """
        Returns the live number in stock, which is
        ``self.num_in_stock - num in carts``. Also caches the value
        for subsequent lookups.
        """
        if self.num_in_stock is None:
            return None
        if not hasattr(self, "_cached_num_in_stock"):
            num_in_stock = self.num_in_stock
            carts = Cart.objects.current()
            items = VendorCartItem.objects.filter(item__variation=self.variation, vendor=self.vendor,
                                                  item__cart__in=carts)
            aggregate = items.aggregate(quantity_sum=models.Sum("quantity"))
            num_in_carts = aggregate["quantity_sum"]
            if num_in_carts is not None:
                num_in_stock = num_in_stock - num_in_carts
            self._cached_num_in_stock = num_in_stock
        return self._cached_num_in_stock


class VendorCartItemMetaClass(ModelBase):
    """
    Metaclass for the ``VendorCartItem`` model that dynamically
    assigns a property to access each field on the ``Vendor``
    """

    def __new__(cls, name, bases, attrs):
        def prop(field):
            def err(self, value):
                raise AssertionError(
                    'To set the Vendor {} property, you need to set directly via vendor using item.vendor.{}'.format(
                        field,
                        field))

            return property(
                lambda self: getattr(self.vendor, field),
                err
                # lambda self, value:    setattr(self.vendor, field, value)
            )

        base_fields = [field.attname for base in bases if hasattr(base, '_meta') for field in base._meta.fields]

        # Only assign new attrs if not a proxy model.
        # For each Vendor field, assign getters directly from the VendorCartItem model
        for field in Vendor._meta.fields:
            if field.name in attrs or field.name in base_fields:
                raise ImproperlyConfigured("A field with the same name exists in both Vendor and VendorCartItem.")
            if field.attname not in ['id', '_order']:
                attrs[field.attname] = prop(field.attname)
        args = (cls, name, bases, attrs)
        return super().__new__(*args)


class VendorCartItem(models.Model, metaclass=VendorCartItemMetaClass):
    vendor = models.ForeignKey(Vendor, verbose_name="Vendor", on_delete=models.CASCADE)
    item = models.ForeignKey('shop.CartItem', verbose_name="Cart Item", related_name="vendors")
    quantity = models.IntegerField(_("Quantity"), default=0, null=False)

    class Meta:
        unique_together = ('item', 'vendor')
        order_with_respect_to = 'item'

    def __str__(self):
        return '%s: %s - %s' % (self.item, self.vendor, self.quantity)
