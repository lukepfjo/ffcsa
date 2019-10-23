from django.apps import AppConfig
from multiurl import multiurl, ContinueResolving
from django.core import urlresolvers
from django.conf.urls import url as create_url, RegexURLPattern, RegexURLResolver
from django.http import Http404

from mezzanine.conf import settings

_slash = "/" if settings.APPEND_SLASH else ""


class ShopConfig(AppConfig):
    name = "cartridge.shop"

    def ready(self):
        """
        Dynamically add the category_product url when the app is ready. This is b/c it needs to be added 2nd to last,
        right before the page url b/c it is almost a catch all.

        we use multiurl to forward to the page url if the category_product view throws a 404, as it will catch 
        non-product slugs
        """
        from cartridge.shop import views
        urls = urlresolvers.get_resolver()

        def add_product_category_url(urls):
            for url in urls.url_patterns:
                if isinstance(url, RegexURLResolver):
                    add_product_category_url(url)
                elif isinstance(url, RegexURLPattern) and url.name == 'page':
                    # category_product url is almost a catch all, so it needs to go
                    # last. using multiurl, if it fails to find a product, then we
                    # will go to the catch-all page url
                    pageurl = urls.url_patterns.pop()
                    urls.url_patterns.append(
                        multiurl(
                            create_url("^(?P<category_slug>.+)/(?P<slug>.+)%s$" % _slash,
                                views.category_product, name="shop_category_product"),
                            pageurl,
                            catch=(Http404, ContinueResolving)
                        )
                    )
                    return

        add_product_category_url(urls)
