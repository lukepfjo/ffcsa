from django import forms
from django.db import transaction
from django.urls import reverse
from mezzanine.accounts import forms as accounts_forms
from mezzanine.conf import settings
from mezzanine.core.request import current_request
from mezzanine.utils.email import send_mail_template

from ffcsa.core.google import update_contact as update_google_contact
from ffcsa.core import sendinblue
from ffcsa.core.utils import give_emoji_free_text
from ffcsa.shop.utils import clear_shipping, set_home_delivery, recalculate_remaining_budget


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

    class Media:
        js = ('js/forms/profile/profile_form.js',)

    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)

        del self.fields['first_name'].widget.attrs['autofocus']

        self.fields['delivery_address'].widget.attrs['readonly'] = ''
        self.fields['delivery_address'].widget.attrs['class'] = 'mb-3 mr-4'
        self.fields['delivery_notes'].widget.attrs = {'rows': 3, 'cols': 40,
                                                      'placeholder': 'Any special notes to give to our delivery driver regarding your delivery/location.'}

        self.fields['phone_number'].widget.attrs['placeholder'] = '123-456-7890'
        self.fields['phone_number_2'].widget.attrs['placeholder'] = '123-456-7890'
        self.fields['drop_site'] = forms.ChoiceField(
            choices=settings.DROP_SITE_CHOICES, label="Drop Site Location")

        if self.instance.id is not None:
            self.initial['drop_site'] = self.instance.profile.drop_site

        if self._signup:
            self.fields['pickup_agreement'] = forms.BooleanField(
                label="I agree to bring my own bags and coolers as needed to pick up my product. The containers "
                      "that the product arrives in stay at the dropsite. I intend to maintain my membership with the FFCSA "
                      "for 6 months, with a minimum payment of $172 per month.")

            # self.fields[''] = forms.FileField(label="Signed Member Product Liability Agreement",
            self.fields['best_time_to_reach'] = forms.CharField(label="What is the best time to reach you?",
                                                                required=True)
            self.fields['communication_method'] = forms.ChoiceField(
                label="What is your preferred method of communication?", required=True,
                choices=(("Email", "Email"), ("Phone", "Phone"), ("Text", "Text")))
            self.fields['num_children'] = forms.IntegerField(label="How many children are in your family?",
                                                             required=True, min_value=0)
            self.fields['hear_about_us'] = forms.CharField(label="How did you hear about us?", required=True,
                                                           widget=forms.Textarea(attrs={'rows': 3}))
            # self.fields['payment_agreement'].required = True
            self.initial['num_adults'] = None
        else:
            # All fields (only checkboxes?) must be rendered in the form unless they are included in settings.ACCOUNTS_PROFILE_FORM_EXCLUDE_FIELDS
            # Otherwise they will be reset/overridden
            self.fields['payment_agreement'].widget = forms.HiddenInput()
            self.fields['join_dairy_program'].widget = forms.HiddenInput()
            self.fields['num_adults'].widget = forms.HiddenInput()

        if not settings.HOME_DELIVERY_ENABLED:
            del self.fields['home_delivery']

    def get_profile_fields_form(self):
        return ProfileFieldsForm

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get('home_delivery', False):
            if not cleaned_data['delivery_address']:
                self.add_error('delivery_address', 'Please provide an address for your delivery.')
        elif not cleaned_data.get('drop_site', None):
            self.add_error('drop_site', 'Please either choose a drop_site or home delivery.')

        return cleaned_data

    def save(self, *args, **kwargs):
        with transaction.atomic():
            user = super(ProfileForm, self).save(*args, **kwargs)

            user.profile.drop_site = self.cleaned_data['drop_site']

            if self._signup:
                user.profile.notes = "<b>Best time to reach:</b>  {}<br/>" \
                                     "<b>Preferred communication method:</b>  {}<br/>" \
                                     "<b>Adults in family:</b>  {}<br/>" \
                                     "<b>Children in family:</b>  {}<br/>" \
                                     "<b>How did you hear about us:</b>  {}<br/>" \
                    .format(self.cleaned_data['best_time_to_reach'],
                            self.cleaned_data['communication_method'],
                            self.cleaned_data['num_adults'],
                            self.cleaned_data['num_children'],
                            self.cleaned_data['hear_about_us'])
                # defaults
                user.profile.allow_substitutions = True
                user.profile.weekly_emails = True
                user.profile.no_plastic_bags = False

            user.profile.save()

        request = current_request()
        if not self._signup:
            # we can't set this on signup b/c the cart.user_id has not been set yet
            if "home_delivery" in self.changed_data:
                if user.profile.home_delivery:
                    set_home_delivery(request)
                else:
                    clear_shipping(request)
                recalculate_remaining_budget(request)

            update_google_contact(user)

            drop_site_list = sendinblue.HOME_DELIVERY_LIST if user.profile.home_delivery else self.cleaned_data[
                'drop_site']

            weekly_email_lists = ['WEEKLY_NEWSLETTER']
            lists_to_add = weekly_email_lists if user.profile.weekly_emails else None
            lists_to_remove = weekly_email_lists if not user.profile.weekly_emails else None
            sendinblue.update_or_add_user(self.cleaned_data['email'], self.cleaned_data['first_name'],
                                          self.cleaned_data['last_name'], drop_site_list,
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

    def clean_delivery_notes(self):
        return give_emoji_free_text(self.cleaned_data['delivery_notes'])

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
