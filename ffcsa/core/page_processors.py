from cartridge.shop.models import Product, Category, ProductVariation
from cartridge.shop.utils import recalculate_cart
from django.contrib.messages import info, error
from django.shortcuts import redirect
from mezzanine.pages.page_processors import processor_for

from ffcsa.core.forms import wrap_AddProductForm


@processor_for("weekly-box", exact_page=True)
def weekly_box(request, page):
    """
    Add all products in the weekly-box category to the users cart
    """
    if request.method == "POST" and request.POST.get('add_box_items'):
        box_contents = Product.objects.published(for_user=request.user
                                                 ).filter(page.category.filters()).distinct()

        remaining_budget = request.cart.remaining_budget()
        info(request, "Box items added to order")

        for item in box_contents:
            variation = item.variations.first()
            if not item.available:
                info(request, "{} is no longer available".format(item.title))
            elif remaining_budget < variation.price():
                error(request, "You are over you budgeted amount")
                break
            elif not variation.has_stock(1):
                info(request, "{} is out of stock".format(item.title))
            else:
                request.cart.add_item(variation, 1)
                remaining_budget -= variation.price()

        recalculate_cart(request)
        return redirect("shop_cart")

    return {}


@processor_for(Category, exact_page=True)
def category_processor(request, page):
    """
    Add the specified item to the users cart
    """
    if request.method == "POST" and request.POST.get('add_item'):
        item_id = request.POST.get("item_id")
        item_qty = request.POST.get("item_qty")

        if item_id and item_qty:
            item = Product.objects.published(for_user=request.user).filter(id=item_id).first()

            if item:
                # use AddProductForm b/c it does some validation w/ inventories, etc
                form = wrap_AddProductForm(request.cart)({'quantity': item_qty}, product=item, to_cart=True)
                if form.is_valid():
                    request.cart.add_item(form.variation, int(item_qty))
                    recalculate_cart(request)
                    info(request, "Item added to order")
                else:
                    for field, error_list in form.errors.items():
                        for e in error_list:
                            if field == '__all__':
                                error(request, e)
                            else:
                                error(request, "{}: {}".format(field, e))
            else:
                error(request, "No Item Found")
        elif not item_qty:
            error(request, "Please enter a quantity")

    return {}
