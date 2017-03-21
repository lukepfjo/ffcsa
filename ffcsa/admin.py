from __future__ import unicode_literals

from django.contrib import admin

from mezzanine.generic.models import ThreadedComment

#TODO get this working and remove all unecessary admin menus
print("unregistering something")
admin.site.unregister(ThreadedComment)
