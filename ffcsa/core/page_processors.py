from cartridge.shop.forms import AddProductForm
from cartridge.shop.models import Product, Category
from cartridge.shop.utils import recalculate_cart
from django.contrib.messages import info, error
from django.shortcuts import redirect
from mezzanine.pages.page_processors import processor_for


@processor_for("weekly-box", exact_page=True)
def weekly_box(request, page):
    """
    Add all products in the weekly-box category to the users cart
    """
    if request.method == "POST" and request.POST.get('add_box_items'):
        box_contents = Product.objects.published(for_user=request.user
                                                 ).filter(page.category.filters()).distinct()
        for item in box_contents:
            request.cart.add_item(item.variations.first(), 1)

        recalculate_cart(request)
        info(request, "Box items added to order")
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
                form = AddProductForm({'quantity': item_qty}, product=item, to_cart=True)
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
