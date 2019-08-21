from __future__ import absolute_import, unicode_literals
import os

from django import VERSION as DJANGO_VERSION
from django.utils.translation import ugettext_lazy as _

##############################
# FFCSA-CORE SETTINGS #
##############################
ORDER_CUTOFF_DAY = 3
SIGNUP_FEE_IN_CENTS = 10000
FEED_A_FRIEND_USER = 'feed.a.friend.ffcsa.fund'
DROP_SITE_CHOICES = (
    ('Farm', 'Junction City - Deck Family Farm (Friday)'),
    ('Corner Market', 'Eugene - The Corner Market (Saturday)'),
    ('LCFM', 'Eugene - Lane County Farmers Market (Saturday)'),
    ('Hollywood', 'Portland - Hollywood Farmers Market (Saturday)'),
    ('PSU', 'Portland - PSU Farmers Market (Saturday)'),
    ('St Johns', 'Portland - St Johns Farmers Market (Saturday)'),
    ('Woodstock', 'Portland - Woodstock Farmers Market (Sunday)'),
    ('Banzhaf', 'Corvallis - Member Drop Site (Saturday 12pm-2pm)'),
)

GOOGLE_GROUP_IDS = {
    "MEMBERS": "contactGroups/71b7ef9a09789cab",
    "NEWSLETTER": "contactGroups/3095ba340cae4e15",
    "MANAGED": "contactGroups/41aaae0b0f3d9da7",
}

##############################
# FFCSA-INVITES SETTINGS #
##############################

INVITE_CODE_LENGTH = 20
INVITE_CODE_USAGE_WINDOW = 7
INVITE_CODE_EXPIRY_DAYS = 0

######################
# CARTRIDGE SETTINGS #
######################

# The following settings are already defined in cartridge.shop.defaults
# with default values, but are common enough to be put here, commented
# out, for conveniently overriding. Please consult the settings
# documentation for a full list of settings Cartridge implements:
# http://cartridge.jupo.org/configuration.html#default-settings

# Sequence of available credit card types for payment.
# SHOP_CARD_TYPES = ("Mastercard", "Visa", "Diners", "Amex")

# Setting to turn on featured images for shop categories. Defaults to False.
# SHOP_CATEGORY_USE_FEATURED_IMAGE = True

# Set an alternative OrderForm class for the checkout process.
# SHOP_CHECKOUT_FORM_CLASS = 'cartridge.shop.forms.OrderForm'

# If True, the checkout process is split into separate
# billing/shipping and payment steps.
# SHOP_CHECKOUT_STEPS_SPLIT = True

# If True, the checkout process has a final confirmation step before
# completion.
# SHOP_CHECKOUT_STEPS_CONFIRMATION = True

# Controls the formatting of monetary values accord to the locale
# module in the python standard library. If an empty string is
# used, will fall back to the system's locale.
# SHOP_CURRENCY_LOCALE = "en_US"

# Dotted package path and name of the function that
# is called on submit of the billing/shipping checkout step. This
# is where shipping calculation can be performed and set using the
# function ``cartridge.shop.utils.set_shipping``.
# SHOP_HANDLER_BILLING_SHIPPING = \
#                       "cartridge.shop.checkout.default_billship_handler"

# Dotted package path and name of the function that
# is called once an order is successful and all of the order
# object's data has been created. This is where any custom order
# processing should be implemented.
# SHOP_HANDLER_ORDER = "cartridge.shop.checkout.default_order_handler"

# Dotted package path and name of the function that
# is called on submit of the payment checkout step. This is where
# integration with a payment gateway should be implemented.
# SHOP_HANDLER_PAYMENT = "cartridge.shop.checkout.default_payment_handler"

# Sequence of value/name pairs for order statuses.
# SHOP_ORDER_STATUS_CHOICES = (
#     (1, "Unprocessed"),
#     (2, "Processed"),
# )

# Sequence of value/name pairs for types of product options,
# eg Size, Colour. NOTE: Increasing the number of these will
# require database migrations!
SHOP_OPTION_TYPE_CHOICES = ()

# Sequence of indexes from the SHOP_OPTION_TYPE_CHOICES setting that
# control how the options should be ordered in the admin,
# eg for "Colour" then "Size" given the above:
# SHOP_OPTION_ADMIN_ORDER = (2, 1)

SHOP_USE_WISHLIST = False
SHOP_USE_VARIATIONS = False
SHOP_USE_UPSELL_PRODUCTS = False
SHOP_USE_RELATED_PRODUCTS = False
SHOP_USE_RATINGS = False
SHOP_PAYMENT_STEP_ENABLED = False
SHOP_DEFAULT_SHIPPING_VALUE = 0
SHOP_CHECKOUT_ACCOUNT_REQUIRED = True
SHOP_CATEGORY_USE_FEATURED_IMAGE = True
SHOP_PRODUCT_SORT_OPTIONS = (('Title', 'title'), ('Recently added', '-date_added'),)
SHOP_CART_EXPIRY_MINUTES = 535600  # valid for 365 days
SHOP_PER_PAGE_CATEGORY = 20
SHOP_HIDE_UNAVAILABLE = True

######################
# MEZZANINE SETTINGS #
######################

PAGES_MENU_SHOW_ALL = False
# SIGNUP_URL =

ACCOUNTS_PROFILE_MODEL = 'ffcsa_core.Profile'
ACCOUNTS_PROFILE_FORM_CLASS = 'ffcsa.core.forms.ProfileForm'
ACCOUNTS_PROFILE_FORM_EXCLUDE_FIELDS = [
    "monthly_contribution",
    "start_date",
    "stripe_customer_id",
    "stripe_subscription_id",
    "payment_method",
    "ach_status",
    "paid_signup_fee",
    "notes",
    "invoice_notes",
    "non_subscribing_member",
    "can_order",
    "google_person_id"
]
ACCOUNTS_APPROVAL_EMAILS = 'fullfarmcsa@deckfamilyfarm.com'  # used to send notifications of new user accounts

ACCOUNTS_NO_USERNAME = True

# The following settings are already defined with default values in
# the ``defaults.py`` module within each of Mezzanine's apps, but are
# common enough to be put here, commented out, for conveniently
# overriding. Please consult the settings documentation for a full list
# of settings Mezzanine implements:
# http://mezzanine.jupo.org/docs/configuration.html#default-settings

# Controls the ordering and grouping of the admin menu.
#
ADMIN_MENU_ORDER = (
    (_("Shop"), ("shop.Product", "shop.Order", "shop.ProductOption", "shop.DiscountCode",
                 "shop.Sale")),
    # ("Users", ((_("Invites"), "invites.InvitationCode"), "auth.User", "auth.Group",)),
    ("Users", (("auth.User", "auth.Group",))),
    ("Content", ("pages.Page", "blog.BlogPost",
                 (_("Media Library"), "fb_browse"),)),
    ("Site", ("sites.Site", "redirects.Redirect", "conf.Setting")),
)

# A three item sequence, each containing a sequence of template tags
# used to render the admin dashboard.
#
# DASHBOARD_TAGS = (
#     ("blog_tags.quick_blog", "mezzanine_tags.app_list"),
#     ("comment_tags.recent_comments",),
#     ("mezzanine_tags.recent_actions",),
# )

# A sequence of templates used by the ``page_menu`` template tag. Each
# item in the sequence is a three item sequence, containing a unique ID
# for the template, a label for the template, and the template path.
# These templates are then available for selection when editing which
# menus a page should appear in. Note that if a menu template is used
# that doesn't appear in this setting, all pages will appear in it.

PAGE_MENU_TEMPLATES = (
    (1, _("Top navigation bar"), "pages/menus/dropdown.html"),
    (2, _("Left-hand tree"), "pages/menus/tree.html"),
    (3, _("Footer"), "pages/menus/footer.html"),
)

PAGE_MENU_TEMPLATES_DEFAULT = ()

# A sequence of fields that will be injected into Mezzanine's (or any
# library's) models. Each item in the sequence is a four item sequence.
# The first two items are the dotted path to the model and its field
# name to be added, and the dotted path to the field class to use for
# the field. The third and fourth items are a sequence of positional
# args and a dictionary of keyword args, to use when creating the
# field instance. When specifying the field class, the path
# ``django.models.db.`` can be omitted for regular Django model fields.
#
EXTRA_MODEL_FIELDS = (
    (
        "cartridge.shop.models.Cart.user_id",
        "IntegerField",
        (),
        # Keyword args for field class.
        {"blank": False, "null": False, "unique": True},
    ),
    (
        "cartridge.shop.models.Cart.attending_dinner",
        "IntegerField",
        (),
        # Keyword args for field class.
        {"blank": False, "null": False, "default": 0},
    ),
    # can't perform field injection on abstract classes, so we need to do it for both CartItem and OrderItem
    (
        "cartridge.shop.models.CartItem.category",
        "TextField",
        (),
        # Keyword args for field class.
        {"blank": True},
    ),
    (
        "cartridge.shop.models.OrderItem.category",
        "TextField",
        (),
        # Keyword args for field class.
        {"blank": True},
    ),
    (
        "cartridge.shop.models.Order.attending_dinner",
        "IntegerField",
        (),
        # Keyword args for field class.
        {"blank": False, "null": False, "default": 0},
    ),
    (
        "cartridge.shop.models.Order.drop_site",
        "CharField",
        (),
        # Keyword args for field class.
        {"blank": True, "max_length": 255},
    ),
    (
        "cartridge.shop.models.Order.billing_detail_phone_2",
        "CharField",
        (),
        # Keyword args for field class.
        {"verbose_name": "Alt. Phone", "blank": True, "max_length": 255},
    ),
    (
        "cartridge.shop.models.Order.no_plastic_bags",
        "BooleanField",
        (),
        # Keyword args for field class.
        {"verbose_name": "No Plastic Bags", "default": False},
    ),
    (
        "cartridge.shop.models.Order.allow_substitutions",
        "BooleanField",
        (),
        # Keyword args for field class.
        {"verbose_name": "Allow product substitutions", "default": True},
    ),
    (
        "cartridge.shop.models.CartItem.vendor",
        "CharField",
        (),
        # Keyword args for field class.
        {"blank": True, "max_length": 255},
    ),
    (
        "cartridge.shop.models.OrderItem.vendor",
        "CharField",
        (),
        # Keyword args for field class.
        {"blank": True, "max_length": 255},
    ),
    (
        "cartridge.shop.models.ProductVariation.vendor",
        "CharField",
        (),
        # Keyword args for field class.
        {"blank": True, "max_length": 255},
    ),
    # add Vendor Price to ProductVariation & OrderItem
    # change Unit Price to Member Price
    (
        "cartridge.shop.models.Category.order_on_invoice",
        "IntegerField",
        (),
        # Keyword args for field class.
        {"default": 0,
         "help_text": "Order this category will be printed on invoices. If this is a sub-category, this is the order printed within the parent category. 0 will be printed last. And sub-categories will only be sorted if the parent category has this value set"},
    ),
    (
        "cartridge.shop.models.Product.weekly_inventory",
        "BooleanField",
        (),
        # Keyword args for field class.
        {"blank": False, "default": True, "verbose_name": "Weekly Inventory"},
    ),
    (
        "cartridge.shop.models.ProductVariation.weekly_inventory",
        "BooleanField",
        (),
        # Keyword args for field class.
        {"blank": False, "default": True, "verbose_name": "Weekly Inventory"},
    ),
    (
        "cartridge.shop.models.CartItem.weekly_inventory",
        "BooleanField",
        (),
        # Keyword args for field class.
        {"blank": False, "default": True, "verbose_name": "Weekly Inventory"},
    ),
    # can't inject in abstract Priced model, so need to do both Product and ProductVariation
    (
        "cartridge.shop.models.Product.vendor_price",
        "cartridge.shop.fields.MoneyField",
        (),
        # Keyword args for field class.
        {"blank": True, "null": True, "verbose_name": "Vendor Price"},
    ),
    (
        "cartridge.shop.models.ProductVariation.vendor_price",
        "cartridge.shop.fields.MoneyField",
        (),
        # Keyword args for field class.
        {"blank": True, "null": True, "verbose_name": "Vendor Price"},
    ),
    (
        "cartridge.shop.models.CartItem.vendor_price",
        "cartridge.shop.fields.MoneyField",
        (),
        # Keyword args for field class.
        {"blank": True, "null": True, "verbose_name": "Vendor Price"},
    ),
    (
        "cartridge.shop.models.OrderItem.vendor_price",
        "cartridge.shop.fields.MoneyField",
        (),
        # Keyword args for field class.
        {"blank": True, "null": True, "verbose_name": "Vendor Price"},
    ),
)

MIGRATION_MODULES = {
    "shop": "ffcsa.core.migrations.shop",
}

# Setting to turn on featured images for blog posts. Defaults to False.
#
# BLOG_USE_FEATURED_IMAGE = True

# If True, the django-modeltranslation will be added to the
# INSTALLED_APPS setting.
USE_MODELTRANSLATION = False

########################
# MAIN DJANGO SETTINGS #
########################

DEFAULT_FROM_EMAIL = "fullfarmcsa@deckfamilyfarm.com"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "default",
    },
    "ffcsa.core.budgets": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "budgets",
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Los_Angeles'

# If you set this to True, Django will use timezone-aware datetimes.
USE_TZ = True

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = "en"

# Supported languages
LANGUAGES = (
    ('en', _('English')),
)

# A boolean that turns on/off debug mode. When set to ``True``, stack traces
# are displayed for error pages. Should always be set to ``False`` in
# production. Best set to ``True`` in local_settings.py
DEBUG = False

# Whether a user's session cookie expires when the Web browser is closed.
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# The age of session cookies, in seconds.
# SESSION_COOKIE_AGE = 2419200

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

AUTHENTICATION_BACKENDS = ["mezzanine.core.auth_backends.MezzanineBackend"]

# The numeric mode to set newly-uploaded files to. The value should be
# a mode you'd pass directly to os.chmod.
FILE_UPLOAD_PERMISSIONS = 0o644

#############
# DATABASES #
#############

DATABASES = {
    "default": {
        # Add "postgresql_psycopg2", "mysql", "sqlite3" or "oracle".
        "ENGINE": "django.db.backends.",
        # DB name or path to database file if using sqlite3.
        "NAME": "",
        # Not used with sqlite3.
        "USER": "",
        # Not used with sqlite3.
        "PASSWORD": "",
        # Set to empty string for localhost. Not used with sqlite3.
        "HOST": "",
        # Set to empty string for default. Not used with sqlite3.
        "PORT": "",
    }
}

#########
# PATHS #
#########

# Full filesystem path to the project.
PROJECT_APP_PATH = os.path.dirname(os.path.abspath(__file__))
PROJECT_APP = os.path.basename(PROJECT_APP_PATH)
PROJECT_ROOT = BASE_DIR = os.path.dirname(PROJECT_APP_PATH)

# Every cache key will get prefixed with this value - here we set it to
# the name of the directory the project is in to try and use something
# project specific.
CACHE_MIDDLEWARE_KEY_PREFIX = PROJECT_APP

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = "/static/"

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(PROJECT_ROOT, STATIC_URL.strip("/"))

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = STATIC_URL + "media/"

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, *MEDIA_URL.strip("/").split("/"))

# Package/module name to import the root urlpatterns from for the project.
ROOT_URLCONF = "%s.urls" % PROJECT_APP

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(PROJECT_ROOT, "original_templates")
        ],
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.static",
                "django.template.context_processors.media",
                "django.template.context_processors.request",
                "django.template.context_processors.tz",
                "mezzanine.conf.context_processors.settings",
                "mezzanine.pages.context_processors.page",
            ],
            "builtins": [
                "mezzanine.template.loader_tags",
            ],
            "loaders": [
                "mezzanine.template.loaders.host_themes.Loader",
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
        },
    },
]

if DJANGO_VERSION < (1, 9):
    del TEMPLATES[0]["OPTIONS"]["builtins"]

################
# APPLICATIONS #
################

INSTALLED_APPS = (
    "ffcsa.theme",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.redirects",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.sitemaps",
    "django.contrib.staticfiles",
    "mezzanine.boot",
    "mezzanine.conf",
    "mezzanine.core",
    "mezzanine.generic",
    "mezzanine.pages",
    "cartridge.shop",
    # "mezzanine.blog",
    "mezzanine.forms",
    "mezzanine.galleries",
    # "mezzanine.twitter",
    "mezzanine.accounts",
    # "ffcsa.invites",
    "ffcsa.core",
    # "mezzanine.mobile",
)

# List of middleware classes to use. Order is important; in the request phase,
# these middleware classes will be applied in the order given, and in the
# response phase the middleware will be applied in reverse order.
MIDDLEWARE_CLASSES = (
    "mezzanine.core.middleware.UpdateCacheMiddleware",

    'django.contrib.sessions.middleware.SessionMiddleware',
    # Uncomment if using internationalisation or localisation
    # 'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "cartridge.shop.middleware.ShopMiddleware",
    "mezzanine.core.request.CurrentRequestMiddleware",
    "mezzanine.core.middleware.RedirectFallbackMiddleware",
    "mezzanine.core.middleware.AdminLoginInterfaceSelectorMiddleware",
    "mezzanine.core.middleware.SitePermissionMiddleware",
    # Uncomment the following if using any of the SSL settings:
    # "mezzanine.core.middleware.SSLRedirectMiddleware",
    # "mezzanine.pages.middleware.PageMiddleware",
    "cartridge.shop.middleware.MultiurlPageMiddleware",
    "mezzanine.core.middleware.FetchFromCacheMiddleware",
    "ffcsa.core.middleware.DiscountMiddleware",
    "ffcsa.core.middleware.BudgetMiddleware",
)

# Store these package names here as they may change in the future since
# at the moment we are using custom forks of them.
PACKAGE_NAME_FILEBROWSER = "filebrowser_safe"
PACKAGE_NAME_GRAPPELLI = "grappelli_safe"

#########################
# OPTIONAL APPLICATIONS #
#########################

# These will be added to ``INSTALLED_APPS``, only if available.
OPTIONAL_APPS = (
    "debug_toolbar",
    "django_extensions",
    "compressor",
    PACKAGE_NAME_FILEBROWSER,
    PACKAGE_NAME_GRAPPELLI,
)

##################
# LOCAL SETTINGS #
##################

# Allow any settings to be defined in local_settings.py which should be
# ignored in your version control system allowing for settings to be
# defined per machine.

# Instead of doing "from .local_settings import *", we use exec so that
# local_settings has full access to everything defined in this module.
# Also force into sys.modules so it's visible to Django's autoreload.

f = os.path.join(PROJECT_APP_PATH, "local_settings.py")
if os.path.exists(f):
    import sys
    import imp

    module_name = "%s.local_settings" % PROJECT_APP
    module = imp.new_module(module_name)
    module.__file__ = f
    sys.modules[module_name] = module
    exec(open(f, "rb").read())

####################
# DYNAMIC SETTINGS #
####################

# set_dynamic_settings() will rewrite globals based on what has been
# defined so far, in order to provide some better defaults where
# applicable. We also allow this settings module to be imported
# without Mezzanine installed, as the case may be when using the
# fabfile, where setting the dynamic settings below isn't strictly
# required.
try:
    from mezzanine.utils.conf import set_dynamic_settings
except ImportError:
    pass
else:
    set_dynamic_settings(globals())

import sys

if 'test' in sys.argv or 'test_coverage' in sys.argv:  # Covers regular testing and django-coverage
    DATABASES['default']['ENGINE'] = 'django.db.backends.sqlite3'

# This is here b/c fab file does string interpolationn & fails w/ the format string below
if not DEBUG:
    # https://lincolnloop.com/blog/django-logging-right-way/
    import logging.config

    LOGGING_CONFIG = None
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'console': {
                # exact format is not important, this is the minimum information
                'format': '%(asctime)-4s %(name)-12s %(levelname)-8s %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'console',
            },
        },
        'loggers': {
            '': {
                'handlers': ['console'],
                'level': os.getenv('DJANGO_LOG_LEVEL', 'WARNING'),
            },
            'ffcsa_core': {
                'handlers': ['console'],
                'level': 'INFO',
                # required to avoid double logging with root logger
                'propagate': False,
            },
            'invites': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
            },
            'django.request': {
                # don't send WARNING's to rollbar. These occur when 404s happen
                'handlers': ['console'],
                'level': 'WARNING',
                'propagate': False,
            }
        }
    })
