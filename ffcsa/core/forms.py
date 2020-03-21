from django import forms
from django.urls import reverse
from mezzanine.accounts import forms as accounts_forms
from mezzanine.conf import settings
from mezzanine.utils.email import send_mail_template

from ffcsa.core.google import update_contact as update_google_contact
from ffcsa.core import sendinblue


class CartDinnerForm(forms.Form):
    attending_dinner = forms.IntegerField(
        min_value=0, label="Attending dinner at the farm?", required=False)

    def __init__(self, request, data=None, initial=None, **kwargs):
        self._cart = request.cart

        if not data:
            data = {'attending_dinner': self._cart.attending_dinner}

        super(CartDinnerForm, self).__init__(
            data=data, initial=initial, **kwargs)

    def save(self):
        if 'attending_dinner' in self.changed_data:
            self._cart.attending_dinner = self.cleaned_data['attending_dinner']
            self._cart.save()


# monkey patch the cart item form to use custom clean_quantity method
# TODO update sku for CartItem when product sku changes
# original_cart_item_clean_quantity = deepcopy(CartItemForm.clean_quantity)


# def cart_item_clean_quantity(self):
#     # if the sku was changed while a product was in the cart, an exception will be thrown while trying to update the
#     # inventory. Since we don't use inventory much we want to catch that exception and ignore the error, acknowledging
#     # that we may have more in stock then inventory mentions
#     try:
#         variation = ProductVariation.objects.get(sku=self.instance.sku)
#         if not variation.product.available:
#             # setting the following will let django delete the item
#             self.fields['DELETE'].disabled = True
#             self.fields['DELETE'].initial = True
#             self.initial['DELETE'] = True
#             self.add_error(None,
#                            _("'%s' was removed from your cart as it is no longer available." % variation.product.title))
#             return 0
#         return original_cart_item_clean_quantity(self)
#     except ProductVariation.DoesNotExist:
#         return 0


# CartItemForm.clean_quantity = cart_item_clean_quantity

class ProfileForm(accounts_forms.ProfileForm):
    # NOTE: Any fields on the profile that we don't include in this form need to be added to settings.py ACCOUNTS_PROFILE_FORM_EXCLUDE_FIELDS
    username = None

    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)

        self.fields['phone_number'].widget.attrs['placeholder'] = '123-456-7890'
        self.fields['phone_number_2'].widget.attrs['placeholder'] = '123-456-7890'
        self.fields['drop_site'] = forms.ChoiceField(
            choices=settings.DROP_SITE_CHOICES, label="Drop Site Location")

        if self.instance.id is not None:
            self.initial['drop_site'] = self.instance.profile.drop_site

        if self._signup:
            self.fields['pickup_agreement'] = forms.BooleanField(
                label="I agree to bring my own bags and coolers as needed to pick up my product as the containers the product arrives stay at the dropsite.")
            # self.fields[''] = forms.FileField(label="Signed Member Product Liability Agreement",
            self.fields['best_time_to_reach'] = forms.CharField(label="What is the best time to reach you?",
                                                                required=True)
            self.fields['communication_method'] = forms.ChoiceField(
                label="What is your preferred method of communication?", required=True,
                choices=(("Email", "Email"), ("Phone", "Phone"), ("Text", "Text")))
            self.fields['family_stats'] = forms.CharField(label="How many adults and children are in your family?",
                                                          required=True, widget=forms.Textarea(attrs={'rows': 3}))
            self.fields['hear_about_us'] = forms.CharField(label="How did you hear about us?", required=True,
                                                           widget=forms.Textarea(attrs={'rows': 3}))
            self.fields['payment_agreement'].required = True
            self.fields['product_agreement'].required = True
        else:
            self.fields['payment_agreement'].widget = forms.HiddenInput()
            del self.fields['product_agreement']

    def get_profile_fields_form(self):
        return ProfileFieldsForm

    def save(self, *args, **kwargs):
        user = super(ProfileForm, self).save(*args, **kwargs)

        user.profile.drop_site = self.cleaned_data['drop_site']

        if self._signup:
            user.profile.notes = "<b>Best time to reach:</b>  {}<br/>" \
                                 "<b>Preferred communication method:</b>  {}<br/>" \
                                 "<b>Adults and children in family:</b>  {}<br/>" \
                                 "<b>How did you hear about us:</b>  {}<br/>" \
                .format(self.cleaned_data['best_time_to_reach'],
                        self.cleaned_data['communication_method'],
                        self.cleaned_data['family_stats'],
                        self.cleaned_data['hear_about_us'])
            # defaults
            user.profile.allow_substitutions = True
            user.profile.weekly_emails = True
            user.profile.no_plastic_bags = False

        user.profile.save()

        if not self._signup:
            update_google_contact(user)

            weekly_email_lists = ['WEEKLY_NEWSLETTER', 'WEEKLY_REMINDER']
            lists_to_add    = weekly_email_lists if user.profile.weekly_emails else None
            lists_to_remove = weekly_email_lists if not user.profile.weekly_emails else None
            sendinblue.update_or_add_user(self.cleaned_data['email'], self.cleaned_data['first_name'],
                                          self.cleaned_data['last_name'], self.cleaned_data['drop_site'],
                                          self.cleaned_data['phone_number'], lists_to_add, lists_to_remove)

        return user


class ProfileFieldsForm(accounts_forms.ProfileFieldsForm):
    def sanitize_phone_number(self, num):
        if not num or not num.strip():
            return num
        num = num.replace('(', '').replace(')', '').replace(
            ' ', '').replace('-', '').strip()

        if len(num) > 10 and num.startswith('1'):
            return '1-' + num[1:4] + '-' + num[4:7] + '-' + num[7:]

        return num[:3] + '-' + num[3:6] + '-' + num[6:]

    def clean_phone_number(self):
        num = self.cleaned_data['phone_number']
        return self.sanitize_phone_number(num)

    def clean_phone_number_2(self):
        num = self.cleaned_data['phone_number_2']
        return self.sanitize_phone_number(num)


class BasePaymentFormSet(forms.BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        if 'request' in kwargs:
            self.request = kwargs.pop('request')

        super(BasePaymentFormSet, self).__init__(*args, **kwargs)

    def add_fields(self, form, index):
        super(BasePaymentFormSet, self).add_fields(form, index)
        form.fields['notify'] = forms.BooleanField(
            label="Notify User", initial=True, required=False)

    def save(self, commit=True):
        super(BasePaymentFormSet, self).save(commit)

        for d in self.cleaned_data:
            if d and d['notify']:
                send_mail_template(
                    "FFCSA Credit",
                    "ffcsa_core/applied_credit_email",
                    settings.DEFAULT_FROM_EMAIL,
                    d['user'].email,
                    fail_silently=True,
                    context={
                        'first_name': d['user'].first_name,
                        'amount': d['amount'],
                        'notes': d['notes'],
                        'payments_url': self.request.build_absolute_uri(reverse("payments")) if self.request else None
                    }
                )
