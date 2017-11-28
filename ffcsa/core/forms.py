from cartridge.shop.forms import CartItemForm
from cartridge.shop.models import ProductVariation
from copy import deepcopy
from django import forms
from mezzanine.pages.admin import PageAdminForm
from . import models


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
        return original_cart_item_clean_quantity(self)
    except ProductVariation.DoesNotExist:
        return 0
