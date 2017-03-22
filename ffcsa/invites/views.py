from __future__ import unicode_literals

from django.contrib.messages import info
from django.contrib.auth import login as auth_login
from django.http import Http404
from django.template.response import TemplateResponse
from django.utils.translation import ugettext_lazy as _

from mezzanine.utils.urls import login_redirect

from .forms import ProfileForm


def signup(request, template="accounts/account_signup.html",
           extra_context=None):
    """
    invitation only signup form.
    """
    if not (request.GET.get('code') and request.GET.get('email')):
        raise Http404('You must have an invitation code to signup')

    form = ProfileForm(
        request.POST or None,
        initial={'code': request.GET.get('code'), 'email': request.GET.get('email')}
    )

    if request.method == "POST" and form.is_valid():
        new_user = form.save()
        info(request, _("Successfully signed up"))
        auth_login(request, new_user)
        return login_redirect(request)
    context = {"form": form, "title": _("Sign up")}
    context.update(extra_context or {})
    return TemplateResponse(request, template, context)
