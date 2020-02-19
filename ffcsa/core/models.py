import datetime

from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.db import models
from django.utils.safestring import mark_safe
from mezzanine.core.fields import FileField, RichTextField
from mezzanine.core.models import RichText
from mezzanine.pages.models import Page
from mezzanine.utils.models import upload_to

from ffcsa.shop.fields import MoneyField
from ffcsa.core.managers import PaymentManager

User = get_user_model()


###################
#  User
###################


def patched_str_(self):
    if self.last_name and self.first_name:
        return "{}, {}".format(self.last_name, self.first_name)

    return self.get_username()


User.__str__ = patched_str_

###################
#  Profile
###################


PHONE_REGEX = RegexValidator(regex=r'^\+?(1-)?\d{3}-\d{3}-\d{4}$',
                             message="Phone number must be entered in the format: '999-999-9999'.")


class Profile(models.Model):
    user = models.OneToOneField("auth.User")
    monthly_contribution = MoneyField("Monthly Contribution", decimal_places=2)
    phone_number = models.CharField("Contact Number", validators=[
        PHONE_REGEX], max_length=15)
    phone_number_2 = models.CharField("Alternate Contact Number", validators=[
        PHONE_REGEX], blank=True, max_length=15)
    drop_site = models.CharField("Drop Site", blank=True, max_length=255)
    notes = RichTextField("Customer Notes", blank=True)
    invoice_notes = models.TextField("Invoice Notes", blank=True,
                                     help_text="Use &lt;br/&gt; to enter a newline, and &lt;b&gt;My Text&lt;/b&gt; to make something bold.")
    start_date = models.DateField("CSA Start Date", blank=True, null=True)
    stripe_customer_id = models.CharField(
        blank=True, null=True, max_length=255)
    stripe_subscription_id = models.CharField(
        blank=True, null=True, max_length=255)
    payment_method = models.CharField(blank=False, null=True,
                                      choices=[
                                          ('CC', 'Credit Card'), ('ACH', 'Bank Account'), ('CRYPTO', 'Crypto')],
                                      max_length=255)
    ach_status = models.CharField(blank=False, null=True, max_length=20,
                                  choices=[('NEW', 'Unverified'), ('VERIFYING', 'Verifying'), ('VERIFIED', 'Verified'),
                                           ('FAILED', 'Verification Failed')])
    paid_signup_fee = models.BooleanField(default=False)
    can_order_dairy = models.BooleanField("Has had dairy conversation", default=False)
    payment_agreement = models.BooleanField(
        "I agree to make monthly payments in order to maintain my membership with the FFCSA for 12 months, with a minimium of $172 per month. If I need to change my monthly payment amount, I will notify the FFCSA admin and keep changes to a maximum of two times per year.",
        default=False)
    product_agreement = models.FileField("Liability Agreement Form",
                                         upload_to='uploads/member_docs/',
                                         blank=True,
                                         help_text=mark_safe(
                                             "Please <a target='_blank' href='/static/docs/Product Liability Agreement.pdf'>download this form</a> and have all adult members in your household sign. Then upload here."))
    non_subscribing_member = models.BooleanField(default=False,
                                                 help_text="Non-subscribing members are allowed to make payments to their ffcsa account w/o having a monthly subscription")
    no_plastic_bags = models.BooleanField(default=False,
                                          help_text="Do not pack my items in a plastic bag when possible.")
    allow_substitutions = models.BooleanField(default=True,
                                              help_text="I am okay with substitutions when an item I ordered is no longer available. We do our best to pack what you have ordered, however on occasion crops will not be ready to harvest, etc. We can provide a substitution, or we can credit your account.")
    weekly_emails = models.BooleanField(default=True, verbose_name="Receive Weekly Emails",
                                        help_text="Receive weekly newsletter and reminder emails.")
    google_person_id = models.TextField(
        null=True, help_text="Google Person resource id", blank=True)
    discount_code = models.ForeignKey(
        'shop.DiscountCode', blank=True, null=True, on_delete=models.PROTECT)

    @property
    def joined_before_dec_2017(self):
        # use early nov b/c dec payments are received in nov
        return self.user.date_joined.date() <= datetime.date(2017, 11, 5)

    @property
    def is_member(self):
        return self.paid_signup_fee

    @property
    def is_subscribing_member(self):
        # TODO :: Ensure this properly determines that they are subscribed
        return (self.is_member and (self.stripe_subscription_id is not None)) or self.user.id == 5

    def __str__(self):
        if self.user.last_name and self.user.first_name:
            return "{}, {}".format(self.user.last_name, self.user.first_name)

        return self.user.get_username()


###################
#  Payment
###################


class Payment(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    date = models.DateField('Payment Date', default=datetime.date.today)
    amount = models.DecimalField('Amount', max_digits=10, decimal_places=2)
    pending = models.BooleanField('Pending', default=False)
    notes = models.TextField('Notes', null=True, blank=True)
    charge_id = models.CharField(max_length=255, null=True, blank=True)

    objects = PaymentManager()

    def __str__(self):
        return "%s, %s - %s - $%s" % (self.user.last_name, self.user.first_name, self.date, self.amount)


class Recipe(Page, RichText):
    """
    A recipe with list of products on the website.
    """
    featured_image = FileField(verbose_name="Featured Image",
                               upload_to=upload_to(
                                   "shop.Recipe.featured_image", "shop"),
                               format="Image", max_length=255, null=True, blank=True)
    products = models.ManyToManyField("shop.Product", blank=True,
                                      verbose_name="Products",
                                      through="RecipeProduct")

    class Meta:
        verbose_name = "Recipe"
        verbose_name_plural = "Recipes"


class RecipeProduct(models.Model):
    recipe = models.ForeignKey(
        Recipe, verbose_name="Recipe", on_delete=models.CASCADE)
    product = models.ForeignKey(
        "shop.Product", verbose_name="Product", on_delete=models.CASCADE)
    quantity = models.IntegerField("Quantity", default=1)
