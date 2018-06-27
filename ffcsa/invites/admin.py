from django.contrib import admin
from django.contrib.messages import error, info
from django.urls import reverse
from mezzanine.conf import settings

from .utils import send_invite_code_mail
from .models import InvitationCode


class InvitationCodeAdmin(admin.ModelAdmin):
    list_display = ('registered_to', 'created_date', 'expired')

    def save_model(self, request, obj, form, change):
        if change:
            super(InvitationCodeAdmin, self).save_model(request, obj, form, change)
        else:
            code = InvitationCode.objects.create_invite_code(
                obj.registered_to,
                name=obj.registered_name,
                creator=request.user,
                drop_site=obj.drop_site,
            )
        site_url = request.build_absolute_uri(reverse("home"))
        display_signup_url = request.build_absolute_uri(reverse("mezzanine_signup"))
        signup_url = '{url}?email={email}&code={code}'.format(url=display_signup_url, email=code.registered_to,
                                                              code=code.short_key)
        try:
            send_invite_code_mail(code, site_url, display_signup_url, signup_url)
        except Exception as e:
            if settings.DEBUG:
                raise
            error(request, "There was an error sending mail to %s. [%s]" % (
                code.registered_to, e
            ))
        else:
            info(request, "An Invite has been sent to %s." % code.registered_to)


admin.site.register(InvitationCode, InvitationCodeAdmin)
