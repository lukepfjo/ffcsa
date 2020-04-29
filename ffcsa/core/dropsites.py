from django.conf import settings

_DROPSITE_DICT = {}
DROPSITE_CHOICES = []

for dropsite in settings.DROPSITES:
    name = dropsite['name']
    DROPSITE_CHOICES.append((name, dropsite['description']))
    _DROPSITE_DICT[name] = dropsite


def is_valid_dropsite(user):
    return user.profile.home_delivery or user.profile.drop_site in _DROPSITE_DICT


def get_color(dropsite_name):
    if dropsite_name == 'Home Delivery':
        return 'purple'

    ds = _DROPSITE_DICT[dropsite_name]
    color = ds['color'] if ds else 'white'
    if not ds:
        strokeColor = 'white'
    else:
        strokeColor = color if color is not 'white' else 'black'

    return color, strokeColor


