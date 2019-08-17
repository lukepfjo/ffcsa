import datetime

from django.template.loader import get_template
from django import forms
from django.utils import formats
from mezzanine import template
from ffcsa.core.utils import ORDER_CUTOFF_DAY, DAYS_IN_WEEK, get_friday_pickup_date, get_order_week_start

register = template.Library()


@register.simple_tag()
def pickup_date_text():
    pickup = get_friday_pickup_date()
    delivery = pickup + datetime.timedelta(1)

    return "Weekly order for pickup {} & delivery {}".format(formats.date_format(pickup, "D F d"),
                                                             formats.date_format(delivery, "D F d"))


@register.simple_tag()
def order_week_start():
    week_start = get_order_week_start()

    return formats.date_format(week_start, "F d, Y")


@register.simple_tag()
def order_week_end():
    now = datetime.datetime.now()

    if now.weekday() < ORDER_CUTOFF_DAY:
        delta = ORDER_CUTOFF_DAY - now.weekday() - 1  # subtract 1 so we end the day of the cutoff day
        order_week_end = now + datetime.timedelta(delta)
    else:
        delta = now.weekday() - ORDER_CUTOFF_DAY
        order_week_end = now + datetime.timedelta(DAYS_IN_WEEK - delta)

    return formats.date_format(order_week_end, "F d, Y")


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def get_attr(value, arg):
    return getattr(value, arg)


@register.filter
def get_billing_detail_field(billing_detail_list, key):
    for (k, value) in billing_detail_list:
        if k == key:
            return value

    return None


@register.filter
def is_checkbox(boundfield):
    """Return True if this field's widget is a CheckboxInput."""
    return isinstance(boundfield.field.widget, forms.CheckboxInput)


@register.filter
def is_select(boundfield):
    """Return True if this field's widget is a CheckboxInput."""
    return isinstance(boundfield.field.widget, forms.Select)


@register.simple_tag(takes_context=True)
def fields_for(context, form, *exclude_fields, template="includes/form_fields_exclude.html"):
    """
    Renders fields for a form with an optional template choice.
    """
    context["form_for_fields"] = form
    context["exclude_fields"] = exclude_fields
    return get_template(template).render(context.flatten())


@register.simple_tag(takes_context=True)
def render_field(context, field, **kwargs):
    """
    Renders a single form field
    """
    template = kwargs.get('template', "includes/form_field.html")
    context["field"] = field
    context["show_required"] = True
    context.update(kwargs)
    return get_template(template).render(context.flatten())
