from __future__ import unicode_literals

from django.contrib import admin

from mezzanine.generic.models import ThreadedComment

#TODO remove all unecessary admin menus
admin.site.unregister(ThreadedComment)
