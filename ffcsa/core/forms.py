from cartridge.shop.models import Order
from django import forms
from mezzanine.pages.admin import PageAdminForm


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


class OrderExportForm(forms.Form):
    from_date = forms.DateField(input_formats=['%m-%d-%Y'], widget=forms.TextInput(attrs={'placeholder': '04-01-2017'}))
    to_date = forms.DateField(input_formats=['%m-%d-%Y'], widget=forms.TextInput(attrs={'placeholder': '04-31-2017'}))

    def get_orders(self):
        return Order.objects.filter(time__gte=self.cleaned_data['from_date'], time__lte=self.cleaned_data['to_date'])
