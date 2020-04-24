from ffcsa.shop.models import Product
from ffcsa.shop.utils import recalculate_cart
from django.contrib.messages import info, error
from django.shortcuts import redirect
from mezzanine.conf import settings
from mezzanine.pages.page_processors import processor_for
from mezzanine.utils.urls import slugify
from mezzanine.utils.views import paginate

from ffcsa.core.models import Recipe


@processor_for('recipes', exact_page=True)
def recipies_processor(request, page):
    recipes = []

    for recipe in Recipe.objects.published(for_user=request.user).exclude(slug='recipes'):
        total_products = recipe.products.count()
        available_products = recipe.products.filter(available=True).count()

        if available_products / total_products > .75:
            recipes.append(recipe)

    return {
        'recipes': recipes
    }


@processor_for(Recipe, exact_page=True)
def recipe_processor(request, page):
    """
    Add paging/sorting to the products for the Recipe.
    Add all products in the Recipe to the users cart
    """

    if page.slug == 'recipes':
        return {}

    settings.clear_cache()
    products = page.recipe.recipeproduct_set.filter(
        product__in=page.recipe.products.published())

    if request.method == "POST":
        if not request.user.profile.signed_membership_agreement:
            raise Exception(
                "You must sign our membership agreement before you can make an order")

        if not request.user.profile.home_delivery and request.user.profile.drop_site not in [dropsite_info[0] for
                                                                                             dropsite_info in
                                                                                             settings.DROP_SITE_CHOICES]:
            error(request,
                  "Your current dropsite is no longer available. "
                  "Please select a different dropsite before adding items to your cart.")
            return

        if request.POST.get('add_box_items'):
            if not request.user.profile.can_order_dairy:
                products = products.filter(product__is_dairy=False)

            add_box_items([(p.product, p.quantity) for p in products], request)
        elif request.POST.get('add_item'):
            # TODO handle this case
            pass
        return redirect("shop_cart")

    def prefix_product(field):
        return '-product__' + field[1:] if field.startswith('-') else 'product__' + field

    sort_options = [(slugify(option[0]), prefix_product(option[1]))
                    for option in settings.SHOP_PRODUCT_SORT_OPTIONS]
    sort_by = request.GET.get(
        "sort", sort_options[0][1] if sort_options else '-product__date_added')
    products = paginate(products.order_by(sort_by),
                        request.GET.get("page", 1),
                        settings.SHOP_PER_PAGE_CATEGORY,
                        settings.MAX_PAGING_LINKS)
    products.sort_by = sort_by

    can_order_dairy = request.user.is_authenticated() and request.user.profile.can_order_dairy
    return {"products": products, "can_order_dairy": can_order_dairy}


@processor_for("weekly-box", exact_page=True)
def weekly_box(request, page):
    """
    Add all products in the weekly-box category to the users cart
    """

    if request.method == "POST" and request.POST.get('add_box_items'):
        if not request.user.profile.signed_membership_agreement:
            raise Exception(
                "You must sign our membership agreement before you can make an order")
        if not request.user.profile.home_delivery and request.user.profile.drop_site not in [dropsite_info[0] for
                                                                                             dropsite_info in
                                                                                             settings.DROP_SITE_CHOICES]:
            error(request,
                  "Your current dropsite is no longer available. "
                  "Please select a different dropsite before adding items to your cart.")
            return

        box_contents = Product.objects.published(for_user=request.user
                                                 ).filter(page.category.filters())
        if not request.user.profile.can_order_dairy:
            box_contents.filter(product__is_dairy=False)

        add_box_items([(i, 1) for i in box_contents.distinct()], request)
        return redirect("shop_cart")

    can_order_dairy = request.user.is_authenticated() and request.user.profile.can_order_dairy
    return {"can_order_dairy": can_order_dairy}


def add_box_items(box_contents, request):
    remaining_budget = request.cart.remaining_budget()
    info(request, "Box items added to order")

    for item, quantity in box_contents:
        variation = item.variations.first()
        if not item.available:
            info(request, "{} is no longer available".format(item.title))

        elif remaining_budget < variation.price():
            error(request, "You are over you budgeted amount")
            break

        elif not variation.has_stock(1):
            info(request, "{} is out of stock".format(item.title))

        else:
            request.cart.add_item(variation, quantity)
            remaining_budget -= variation.price() * quantity

    recalculate_cart(request)
