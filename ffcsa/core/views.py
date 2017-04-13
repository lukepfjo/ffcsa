from cartridge.shop import views as s_views
from cartridge.shop.forms import AddProductForm
from cartridge.shop.models import Category
from django.template.response import TemplateResponse
from mezzanine.conf import settings


def shop_home(request, template="shop_home.html"):
    root_categories = Category.objects.published().filter(parent__isnull=True)

    context = {
        'categories': root_categories,
        'settings': settings,
    }

    return TemplateResponse(request, template, context)


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
