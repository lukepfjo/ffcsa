from cartridge.shop import views as s_views
from cartridge.shop.forms import AddProductForm, CartItemFormSet, DiscountForm
from cartridge.shop.models import Category
from django.contrib.messages import info
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
        if request.POST.get('submit_order'):
            cart = request.cart
            cart.submitted = True
            cart.save()

            # need to add "update_cart to POST info so the next view will process the cart
            q = request.POST.copy();
            q.setdefault("update_cart", "true")
            request.POST = q

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

    return s_views.product(request, slug, template=template, form_class=form_class, extra_context=extra_context)
