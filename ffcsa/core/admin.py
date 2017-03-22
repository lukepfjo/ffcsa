from __future__ import unicode_literals

from cartridge.shop.admin import CategoryAdmin
from cartridge.shop.models import Category
from django.contrib import admin

from mezzanine.generic.models import ThreadedComment

from ffcsa.core.forms import CategoryAdminForm


class MyCategoryAdmin(CategoryAdmin):
    form = CategoryAdminForm


admin.site.unregister(Category)
admin.site.register(Category, MyCategoryAdmin)

# TODO remove all unecessary admin menus
admin.site.unregister(ThreadedComment)
