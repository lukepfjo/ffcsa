from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
from mezzanine.conf import register_setting

####################################################################
#  This first set of settings already exists in Mezzanine but can  #
#  be overridden or appended to here .        #
####################################################################

# Append the ffcsa core settings used in templates to the list of settings
# accessible in templates.
register_setting(
    name="TEMPLATE_ACCESSIBLE_SETTINGS",
    description=_("Sequence of setting names available within templates."),
    editable=False,
    default=("ROLLBAR", "GOOGLE_API_KEY", "HOME_DELIVERY_ENABLED"),
    append=True,
)

