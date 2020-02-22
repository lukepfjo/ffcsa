from django.utils.translation import gettext

from mezzanine import template

register = template.Library()


@register.simple_tag()
def cond_trans(condition, if_true, if_false):
    # Translate one of two strings, as dictated by the condition (ternary)
    if condition:
        return gettext(if_true)
    else:
        return gettext(if_false)
