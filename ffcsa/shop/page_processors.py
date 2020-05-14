from __future__ import unicode_literals

from django import forms
from django.contrib.messages import info, error
from django.template.defaultfilters import slugify

from mezzanine.conf import settings
from mezzanine.pages.page_processors import processor_for
from mezzanine.utils.views import paginate

from ffcsa.shop.forms import AddProductForm
from ffcsa.shop.models import Category, Product, ProductVariation
from ffcsa.shop.orders import user_can_order
from ffcsa.shop.utils import recalculate_cart


@processor_for(Category, exact_page=True)
def category_processor(request, page):
    """
    Add paging/sorting to the products for the category.
    """
    settings.clear_cache()
    products = Product.objects \
        .published(for_user=request.user) \
        .filter(page.category.filters()) \
        .filter(available=True) \
        .prefetch_related('variations__vendorproductvariation_set') \
        .prefetch_related('categories__parent__category') \
        .distinct()

    sort_options = [(slugify(option[0]), option[1])
                    for option in settings.SHOP_PRODUCT_SORT_OPTIONS]
    sort_by = request.GET.get(
        "sort", sort_options[0][1] if sort_options else '-date_added')
    products = paginate(products.order_by(sort_by),
                        request.GET.get("page", 1),
                        settings.SHOP_PER_PAGE_CATEGORY,
                        settings.MAX_PAGING_LINKS)

    for product in products.object_list:
        initial_data = {'quantity': 1}
        product.add_form = AddProductForm(None, product=product, initial=initial_data, cart=request.cart,
                                          widget=forms.Select)

    if request.method == "POST" and request.POST.get('add_item'):
        sku = request.POST.get("variation")
        quantity = request.POST.get("quantity")

        can_order, err = user_can_order(request.user)
        if not can_order:
            error(request, err)
            return

        if sku and quantity:
            try:
                variation = ProductVariation.objects.get(sku=sku)
                # use AddProductForm b/c it does some validation w/ inventories, etc
                form = AddProductForm({'quantity': quantity, 'variation': sku}, product=variation.product,
                                      cart=request.cart)
                if form.is_valid():
                    request.cart.add_item(form.variation, int(quantity))
                    recalculate_cart(request)
                    info(request, "Item added to order")
                else:
                    for field, error_list in form.errors.items():
                        for e in error_list:
                            if field == '__all__':
                                error(request, e)
                            else:
                                error(request, "{}: {}".format(field, e))

            except ProductVariation.DoesNotExist:
                error(request, "No product found")

        elif not sku:
            error(request, "Please select a product")

    products.sort_by = sort_by
    sub_categories = page.category.children.published()
    child_categories = Category.objects.filter(id__in=sub_categories)

    can_order_dairy = request.user.is_authenticated() and request.user.profile.can_order_dairy
    return {
        "products": products,
        "child_categories": child_categories,
        "can_order_dairy": can_order_dairy
    }
