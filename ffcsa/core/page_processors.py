from cartridge.shop.models import Category
from mezzanine.pages.page_processors import processor_for


@processor_for(Category)
def shop_page(request, page):
    x = 1;
