import datetime
from functools import reduce

from cartridge.shop import views as s_views
from cartridge.shop.forms import AddProductForm, CartItemFormSet, DiscountForm
from cartridge.shop.models import Category, Order
from decimal import Decimal
from django.contrib.messages import info
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.views.decorators.cache import never_cache
from mezzanine.conf import settings

from ffcsa.core.forms import CartDinnerForm


def shop_home(request, template="shop_home.html"):
    root_categories = Category.objects.published().filter(parent__isnull=True)

    context = {
        'categories': root_categories,
        'settings': settings,
    }

    return TemplateResponse(request, template, context)


@never_cache
def cart(request, template="shop/cart.html",
         cart_formset_class=CartItemFormSet,
         discount_form_class=DiscountForm,
         extra_context={}):
    cart_dinner_form = CartDinnerForm(request, request.POST or None)

    if request.method == "POST":
        if cart_dinner_form.is_valid():
            cart_dinner_form.save()

    extra_context['cart_dinner_form'] = cart_dinner_form

    return s_views.cart(request, template=template, cart_formset_class=cart_formset_class,
                        discount_form_class=discount_form_class, extra_context=extra_context)


def product(request, slug, template="shop/product.html",
            form_class=AddProductForm, extra_context=None):
    """
    extends cartridge shop product view, only allowing authenticated users to add products to the cart
    """
    if request.method == 'POST':
        if not request.user.is_authenticated():
            raise Exception("You must be authenticated in order to add products to your cart")
        if not request.cart.user_id:
            request.cart.user_id = request.user.id
        elif request.cart.user_id != request.user.id:
            raise Exception("Server Error")

    response = s_views.product(request, slug, template=template, form_class=form_class, extra_context=extra_context)

    if isinstance(response, HttpResponseRedirect):
        request.method = 'GET'
        return s_views.product(request, slug, template=template, form_class=form_class, extra_context=extra_context)

    return response


def order_history(request, template="shop/order_history.html"):
    today = datetime.date.today()

    start_date = request.user.profile.start_date if request.user.profile.start_date else request.user.date_joined

    ytd_orders = Order.objects \
        .filter(user_id=request.user.id) \
        .filter(time__gte=start_date)

    ytd_sum = reduce(lambda x, y: x + y.total, ytd_orders, 0)

    month_orders = ytd_orders.filter(time__month=today.month)
    month_sum = reduce(lambda x, y: x + y.total, month_orders, 0)

    weekly_budget = request.user.profile.weekly_budget if request.user.profile.weekly_budget else Decimal(0)
    ytd_contrib = Decimal(request.user.profile.csa_months_ytd()) * weekly_budget * Decimal(4.3333)  # 4.333 wks/month

    extra_context = {
        'ytd_contrib': '{0:.2f}'.format(ytd_contrib),
        'ytd_ordered': ytd_sum,
        'month_contrib': '{0:.2f}'.format(weekly_budget * Decimal(4.3333)),
        'month_ordered': month_sum
    }

    return s_views.order_history(request, template=template, extra_context=extra_context)
