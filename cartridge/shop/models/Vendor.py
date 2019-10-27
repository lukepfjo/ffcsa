from django.db import models
from django.utils.translation import ugettext_lazy as _
from mezzanine.core.fields import FileField
from mezzanine.core.managers import DisplayableManager
from mezzanine.core.models import Displayable, Orderable, RichText
from mezzanine.utils.models import upload_to


class Vendor(RichText, Orderable, Displayable):
    title = models.CharField(_("Name"), max_length=500)
    expiry_date = None
    featured_image = FileField(verbose_name=_("Featured Image"),
                               upload_to=upload_to(
                                   "shop.Vendor.featured_image", "vendors"),
                               format="Image", max_length=255, null=True, blank=True)

    objects = DisplayableManager()

    @property
    def name(self):
        return self.title

    @name.setter
    def name(self, name):
        self.title = name

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

    def __str__(self):
        return '%s: %s' % (self.variation, self.vendor)
