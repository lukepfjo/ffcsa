from cartridge.shop.models import Category
from django.template.response import TemplateResponse
from mezzanine.conf import settings


def shop_home(request, template="shop_home.html"):
    root_categories = Category.objects.filter(parent__isnull=True)

    context = {
        'categories': root_categories,
        'settings': settings,
    }

    return TemplateResponse(request, template, context)
