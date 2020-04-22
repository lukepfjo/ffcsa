from mezzanine.core.templatetags.mezzanine_tags import *


# This replaces the mezzanine fields_for template tag
@register.simple_tag(takes_context=True)
def fields_for(context, form, *exclude_fields, **kwargs):
    """
    Renders fields for a form with an optional template choice.
    """
    template = kwargs.get('template', "includes/form_fields_exclude.html")
    context["form_for_fields"] = form
    context["exclude_fields"] = exclude_fields
    context['include_media'] = True
    context.update(kwargs)
    return get_template(template).render(context.flatten())
