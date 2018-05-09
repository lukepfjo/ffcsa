import datetime

from cartridge.shop.forms import CartItemForm, CartItemFormSet, AddProductForm
from cartridge.shop.models import ProductVariation, Order
from copy import deepcopy
from django import forms
from django.utils.translation import ugettext_lazy as _
from mezzanine.pages.admin import PageAdminForm
from . import models


class OrderAdminForm(forms.ModelForm):
    order_date = forms.DateTimeField(label="Order Date",
                                     initial=datetime.date.today, required=True, disabled=False,
                                     widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = Order
        fields = '__all__'

    def save(self, commit=True):
        order_date = self.cleaned_data.get('order_date', None)
        if order_date:
            self.instance.time = order_date
            # disable auto_now_add so we can add orders in the past
            self.instance._meta.get_field("time").auto_now_add = False
        return super(OrderAdminForm, self).save(commit=commit)

    def clean(self):
        cleaned_data = super(OrderAdminForm, self).clean()
        if cleaned_data['order_date'] and self.instance.time:
            del cleaned_data['order_date']
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


class PaymentForm(forms.ModelForm):
    class Meta:
        model = models.Payment
        fields = '__all__'


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
