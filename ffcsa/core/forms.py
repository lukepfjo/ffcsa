import datetime

from cartridge.shop.forms import CartItemForm, CartItemFormSet, AddProductForm
from cartridge.shop.models import ProductVariation, Order
from copy import deepcopy
from django import forms
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from mezzanine.conf import settings
from mezzanine.pages.admin import PageAdminForm
from mezzanine.accounts import forms as accounts_forms
from mezzanine.utils.email import send_mail_template

from ffcsa.core.google import update_contact

User = get_user_model()


class OrderAdminForm(forms.ModelForm):
    order_date = forms.DateTimeField(label="Order Date",
                                     initial=datetime.date.today, required=True, disabled=False,
                                     widget=forms.DateInput(attrs={'type': 'date'}))
    user = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True).order_by('last_name'))

    class Meta:
        model = Order
        fields = '__all__'

    def save(self, commit=True):
        order_date = self.cleaned_data.get('order_date', None)
        if not self.instance.id and order_date:
            self.instance.time = order_date
            # disable auto_now_add so we can add orders in the past
            self.instance._meta.get_field("time").auto_now_add = False

        user = self.cleaned_data.get('user', None)
        if not self.instance.id and user:
            self.instance.billing_detail_first_name = user.first_name
            self.instance.billing_detail_last_name = user.last_name
            self.instance.billing_detail_email = user.email
            self.instance.drop_site = user.profile.drop_site
            self.instance.billing_detail_phone = user.profile.phone_number
            self.instance.billing_detail_phone_2 = user.profile.phone_number_2
            self.instance.user_id = user.id
        return super(OrderAdminForm, self).save(commit=commit)

    def clean(self):
        cleaned_data = super(OrderAdminForm, self).clean()
        if cleaned_data['order_date'] and self.instance.time:
            del cleaned_data['order_date']

        if not cleaned_data['user'] and (
                    not cleaned_data['billing_detail_first_name'] or not cleaned_data['billing_detail_last_name']):
            raise forms.ValidationError(
                _("Either choose a user, or enter billing_detail_first_name and billing_detail_last_name."))

        return cleaned_data


class CategoryAdminForm(PageAdminForm):
    def clean_content(form):
        # make the content field not required for Category Pages
        return form.cleaned_data.get("content")


class CartDinnerForm(forms.Form):
    attending_dinner = forms.IntegerField(min_value=0, label="Attending dinner at the farm?", required=False)

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
original_cart_item_clean_quantity = deepcopy(CartItemForm.clean_quantity)


def cart_item_clean_quantity(self):
    # if the sku was changed while a product was in the cart, an exception will be thrown while trying to update the
    # inventory. Since we don't use inventory much we want to catch that exception and ignore the error, acknowledging
    # that we may have more in stock then inventory mentions
    try:
        variation = ProductVariation.objects.get(sku=self.instance.sku)
        if not variation.product.available:
            # setting the following will let django delete the item
            self.fields['DELETE'].disabled = True
            self.fields['DELETE'].initial = True
            self.initial['DELETE'] = True
            self.add_error(None,
                           _("'%s' was removed from your cart as it is no longer available." % variation.product.title))
            return 0
        return original_cart_item_clean_quantity(self)
    except ProductVariation.DoesNotExist:
        return 0


CartItemForm.clean_quantity = cart_item_clean_quantity


def wrap_AddProductForm(cart):
    class WrappedAddProductForm(AddProductForm):
        def clean(self):
            cleaned_data = super(WrappedAddProductForm, self).clean()
            if not self._product.available:
                raise forms.ValidationError(_("Product is not currently available."))

            item_total = self.variation.price() * self.cleaned_data['quantity']

            if cart.over_budget(item_total):
                raise forms.ValidationError(_("You are over your budgeted amount."))

            # note: if adding any additional validation, need to update page_processors.weekly_box as well
            return cleaned_data

    return WrappedAddProductForm


# monkey patch the cart item formset to check if cart is overbudget on clean
original_cart_item_formset_clean = deepcopy(CartItemFormSet.clean)


def cart_item_formset_clean(self):
    new_cart_total = 0

    if hasattr(self, 'cleaned_data'):
        for form in self.cleaned_data:
            if not form['DELETE']:
                new_quantity = form['quantity']
                unit_price = form['id'].unit_price

                new_cart_total += unit_price * new_quantity

        # Cart.over_budget takes into account the Cart.total_price() + additional_total
        # b/c we are updating the items in the cart, we need calculate
        # the new cart total. If new_cart_total is less then Cart.total_price()
        # additional_total will be neg number, and over_budget should calculate correctly
        additional_total = new_cart_total - self.instance.total_price()

        # if we get into a state where the cart is over_budget, allow user to only remove items
        if self.instance.over_budget(additional_total) and additional_total > 0:
            error = _("Updating your cart put you over budget. Try removing some items first.")
            # hack b/c shop/views.py.cart doesn't transfer _non_form_errors attr
            self._errors.append(error)
            raise forms.ValidationError(error)

    return original_cart_item_formset_clean(self)


CartItemFormSet.clean = cart_item_formset_clean


class ProfileForm(accounts_forms.ProfileForm):
    # NOTE: Any fields on the profile that we don't include in this form need to be added to settings.py ACCOUNTS_PROFILE_FORM_EXCLUDE_FIELDS
    username = None

    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)

        self.fields['phone_number'].widget.attrs['placeholder'] = '123-456-7890'
        self.fields['phone_number_2'].widget.attrs['placeholder'] = '123-456-7890'
        self.fields['drop_site'] = forms.ChoiceField(choices=settings.DROP_SITE_CHOICES, label="Drop Site Location")

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
            update_contact(user)

        return user


class ProfileFieldsForm(accounts_forms.ProfileFieldsForm):
    def sanitize_phone_number(self, num):
        if not num or not num.strip():
            return num
        num = num.replace('(', '').replace(')', '').replace(' ', '').replace('-', '').strip()

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
        form.fields['notify'] = forms.BooleanField(label="Notify User", initial=True)

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
