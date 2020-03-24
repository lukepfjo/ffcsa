import json
import logging

from urllib.parse import quote as make_url_safe

import requests

from django.utils.html import format_html as make_html_safe


if __name__ == '__main__':
    from ffcsa.ffcsa import settings

    print('sendinblue.py :: loading settings.py directly')
else:
    from django.conf import settings

logger = logging.getLogger(__name__)

_API_KEY = settings.SENDINBLUE_API_KEY
if settings.SENDINBLUE_ENABLED and _API_KEY is None:
    raise Exception('SENDINBLUE_API_KEY is not defined in local_settings.py')

_DEFAULT_HEADERS = {
    'accept': 'application/json',
    'content-type': 'application/json',
    'api-key': _API_KEY
}

_BASE_ENDPOINT = 'https://api.sendinblue.com/v3/'

NEW_USER_LISTS = [
    settings.SENDINBLUE_LISTS['WEEKLY_NEWSLETTER'],
    settings.SENDINBLUE_LISTS['WEEKLY_REMINDER'],
    settings.SENDINBLUE_LISTS['MEMBERS']
]

NEW_USER_LISTS_TO_REMOVE = [
    settings.SENDINBLUE_LISTS['PROSPECTIVE_MEMBERS']
]

HOME_DELIVERY_LIST = 'Home Delivery'


# --------
# General helper functions

def send_request(endpoint, method='GET', query=None, data=None, headers=None):
    """
    Wrapper to simplify Sendinblue request handling

    @param endpoint: Everything after api.sendinblue.com/v3/
    @param method: Relevant HTTP verb for endpoint
    @param query: Dictionary of query parameters for GET requests
    @param data: Dictionary of request payload for POST requests
    @param headers: Dictionary of request headers - 'content-type' and 'api-key' will be overwritten if provided

    @return: Dictionary containing the JSON response; raises descriptive exceptions upon failure
    """

    endpoint = _BASE_ENDPOINT + endpoint.lstrip('/')
    data = json.dumps(data) if data is not None else None
    headers = {} if headers is None else headers
    headers.update(_DEFAULT_HEADERS)

    response = requests.request(method, endpoint, headers=headers, data=data, params=query)

    if response.status_code >= 400:
        if response.status_code < 500:
            response_json = response.json()
            response_error = response_json.get('error', response_json)['message']  # SIB error format is not consistent
            raise Exception('Sendinblue error: HTTP {}: {}'.format(response.status_code, response_error))

        else:
            response_json = response.json()
            response_error = response_json.get('error', response_json)['message']  # SIB error format is not consistent
            raise Exception('Sendinblue internal server error: HTTP {}: {}'.format(response.status_code, response_error))

    try:
        return response.json()
    except json.decoder.JSONDecodeError:
        return response.text


def _initialize_drop_site_lists():
    # Create a dictionary of {drop_site_name: id} of the SIB drop site mailing lists
    # If drop sites in settings.py do not have corresponding lists on SIB, this will create them

    existing_lists = send_request('contacts/lists')
    drop_site_ids = {_list['name'].replace('Dropsite - ', ''): int(_list['id'])
                     for _list in existing_lists['lists']
                     if _list['name'].startswith('Dropsite')}

    # Get the names of the drop_sites from settings.py and diff them with the folders on SIB
    missing_on_sib = [d[0] for d in settings.DROP_SITE_CHOICES if d[0] not in drop_site_ids.keys()]

    if HOME_DELIVERY_LIST not in drop_site_ids.keys():
        missing_on_sib.append(HOME_DELIVERY_LIST)

    if len(missing_on_sib) > 0:
        folders = send_request('contacts/folders')['folders']
        drop_site_folder = [f['id'] for f in folders if f['name'] == settings.SENDINBLUE_DROP_SITE_FOLDER][0]

        for missing_drop_site in missing_on_sib:
            list_name = 'Dropsite - {}'.format(missing_drop_site)
            logger.info('Drop site list "{}" is missing on Sendinblue; creating...'.format(list_name))
            response = send_request('contacts/lists', method='POST',
                                    data={'name': list_name, 'folderId': drop_site_folder})
            drop_site_ids[missing_drop_site] = int(response['id'])

    return drop_site_ids


if settings.SENDINBLUE_ENABLED:
    _DROP_SITE_IDS = _initialize_drop_site_lists()

# --------
# User (contact) management

def _format_phone_number(phone_number):
    # Returns formatted phone number on success, False on failure

    for char in (' ', '-', '(', ')'):
        phone_number = phone_number.replace(char, '')

    if 0 < len(phone_number) < 10:
        return False

    # Lacking country code; assume US
    elif len(phone_number) == 10:
        return '1' + phone_number

    # SIB requires a leading +
    elif len(phone_number) == 11:
        return '' + phone_number

    return phone_number


def get_user(email=None, phone_number=None):
    """
    Returns user data from SIB; either email or phone_number must be provided

    @param email: User's email
    @param phone_number: User's cell phone number (optional; can be used instead of email)

    @return: Dictionary with keys 'email', 'first_name', 'last_name', 'phone_number', 'drop_site', and 'list_ids'
    """

    if email is None and phone_number is None:
        raise Exception('Either email or phone_number must be provided')

    identifier = email if email is not None else phone_number
    user = send_request('contacts/{}'.format(make_url_safe(identifier)))
    attributes = user['attributes']
    list_ids = user['listIds']
    drop_site = [name for name, site_list_id in _DROP_SITE_IDS.items() if site_list_id in list_ids]
    drop_site = drop_site[0] if len(drop_site) != 0 else None

    return {
        'email': user['email'],
        'first_name': attributes['FIRSTNAME'],
        'last_name': attributes['LASTNAME'],
        'phone_number': attributes.get('sms', attributes).get('SMS', None),
        'drop_site': drop_site,
        'list_ids': list_ids
    }


def add_user(email, first_name, last_name, drop_site, phone_number=None):
    """
    Add a new user to SIB. Adds user to the Weekly Newsletter, Weekly Reminder, Members, and provided drop site list

    @param email: Email of user to be added
    @param first_name: User's first name
    @param last_name: User's last name
    @param drop_site: Drop site name, ex: 'Hollywood'
    @param phone_number: User's cellphone number, not required

    @return: (True, '') on success, (False, '<some error message>') on failure
    """
    if not settings.SENDINBLUE_ENABLED:
        return True, ''

    if drop_site not in _DROP_SITE_IDS.keys():
        msg = 'Drop site {} does not exist in settings.DROP_SITE_CHOICES'.format(drop_site)
        logger.error(msg)
        return False, msg

    drop_site_list_id = int(_DROP_SITE_IDS[drop_site])

    phone_number = _format_phone_number(phone_number) if phone_number is not None else None
    if phone_number is False:
        msg = 'Invalid phone number'
        logger.error(msg)
        return False, msg

    body = {
        'updateEnabled': False,
        'email': email,
        'attributes': {
            'FIRSTNAME': first_name,
            'LASTNAME': last_name,
        },
        'listIds': [drop_site_list_id] + NEW_USER_LISTS,
        'unlinkListIds': NEW_USER_LISTS_TO_REMOVE
    }

    if phone_number is not None:
        body['attributes']['SMS'] = phone_number

    try:
        send_request('contacts', 'POST', data=body)

    except Exception as ex:
        if 'Contact already exist' in str(ex):
            msg = 'User already exists'
            logger.error(msg)
            return False, msg
        logger.error(ex)
        # raise ex

    return True, ''


def update_or_add_user(email, first_name, last_name, drop_site, phone_number=None,
                       lists_to_add=None, lists_to_remove=None):
    """
    Updates a user on SIB, or creates a new one should they not exist

    @param email: Email of user to be updated
    @param first_name: User's first name
    @param last_name: User's last name
    @param drop_site: Drop site name, ex: 'Hollywood', or None to remove
    @param phone_number: User's cellphone number, not required
    @param lists_to_add: List of list names that the user desires to be on (other than drop site)
    @param lists_to_remove: List of list names the user does not want to be on (other than drop site)

    @return: (True, '') on success, (False, '<some error message>') on failure
    """
    if not settings.SENDINBLUE_ENABLED:
        return True, ''

    if drop_site is not None and drop_site not in (_[0] for _ in settings.DROP_SITE_CHOICES):
        msg = 'Drop site {} does not exist in settings.DROP_SITE_CHOICES'.format(drop_site)
        logger.error(msg)
        return False, msg

    phone_number = _format_phone_number(phone_number) if phone_number is not None else None
    if phone_number is False:
        msg = 'Invalid phone number'
        logger.error(msg)
        return False, msg

    body = {'attributes': {}, 'listIds': [], 'unlinkListIds': []}

    # Diff the old and new user info
    try:
        old_user_info = get_user(email, phone_number)

    except Exception as ex:
        if 'Contact does not exist' in str(ex):
            add_user(email, first_name, last_name, drop_site, phone_number)
            old_user_info = get_user(email, phone_number)
        else:
            logger.error(ex)
            # raise ex

    new_user_info = {'email': email, 'first_name': first_name, 'last_name': last_name,
                     'drop_site': drop_site, 'phone_number': phone_number}

    to_set = [(k, v) for k, v in new_user_info.items() if old_user_info[k] != v]

    # Nothing to update
    if len(to_set) == 0 and lists_to_add is None and lists_to_remove is None:
        return True, ''

    # Loop through and set attributes in query to their SIB equivalent
    translate_table = {'email': 'EMAIL', 'first_name': 'FIRSTNAME', 'last_name': 'LASTNAME', 'phone_number': 'SMS'}
    for attr_name, attr_value in to_set:
        sib_attr_name = translate_table.get(attr_name, None)

        if sib_attr_name is not None:  # Ignore drop site
            if attr_name == 'phone_number' and attr_value is None:
                body['attributes'][sib_attr_name] = ''
            elif attr_value != '':
                body['attributes'][sib_attr_name] = attr_value

    # Swap drop sites or remove drop site
    old_user_drop_site = old_user_info['drop_site']
    if old_user_drop_site != drop_site:
        if drop_site is not None:
            body['listIds'].append(int(_DROP_SITE_IDS[drop_site]))
        if old_user_drop_site is not None:
            body['unlinkListIds'].append(int(_DROP_SITE_IDS[old_user_drop_site]))

    # Add/remove lists
    if lists_to_add is not None:
        body['listIds'].extend([int(settings.SENDINBLUE_LISTS[desired]) for desired in lists_to_add])
    if lists_to_remove is not None:
        body['unlinkListIds'].extend([int(settings.SENDINBLUE_LISTS[unwanted]) for unwanted in lists_to_remove])

    # Remove empty lists from query
    if len(body['listIds']) == 0:
        del body['listIds']
    if len(body['unlinkListIds']) == 0:
        del body['unlinkListIds']

    try:
        send_request('contacts/{}'.format(make_url_safe(email)), 'PUT', data=body)

    except Exception as ex:
        if 'Invalid phone number' in str(ex):
            msg = 'Invalid phone number'
            logger.error(msg)
            return False, msg
        logger.error(ex)
        # raise ex

    return True, ''


def on_user_cancel_subscription(email, first_name, last_name):
    return update_or_add_user(email, first_name, last_name,
                              drop_site=None,
                              lists_to_add=['FORMER_MEMBERS'],
                              lists_to_remove=['MEMBERS', 'WEEKLY_REMINDER'])


def on_user_resubscribe(email, first_name, last_name, drop_site):
    return update_or_add_user(email, first_name, last_name,
                              drop_site=drop_site,
                              lists_to_add=['MEMBERS'],
                              lists_to_remove=['FORMER_MEMBERS'])

# --------
# Email management

def _get_transactional_email_templates(pprint=True):
    # Gets and pretty-prints the names and IDs of all transactional templates,
    # mostly for easy reference while working in the back-end

    templates = send_request('smtp/templates', query={"temmplateStatus": True})

    templates = templates.get('templates', None)
    if templates is None:
        raise Exception('Sendinblue error: Could not get transactional email templates')

    templates = {t['name']: t['id'] for t in templates}

    if pprint:
        print('Sendinblue Templates: <name>: <id>')
        print(str(templates).replace('{', '{\n\t').replace('}', '\n}').replace(', ', '\n\t'))
    else:
        return templates


def send_transactional_email(template_name, recipient_email):
    """
    Send a transactional email using the provided details

    @param template_name: The name of a template as defined in settings.py
    @param recipient_email: Email of recipient - NOTE: Must be contact on SIB, otherwise this will fail
    @return: True upon success, False on failure
    """

    template_id = settings.SENDINBLUE_TRANSACTIONAL_TEMPLATES.get(template_name, None)
    if template_id is None:
        logger.critical('Sendinblue error: Transactional template "{}" is missing in settings.py'.format(template_name))
        return False

    data = {
        'templateId': template_id,
        'replyTo': {'name': 'Full Farm CSA', 'email': settings.DEFAULT_FROM_EMAIL},
        'to': [{'email': recipient_email}]
    }

    try:
        response = send_request('smtp/email', 'POST', data=data)

    except Exception as ex:
        if 'Contact does not exist' in str(ex):
            logger.error('Sendinblue error: Attempted to send email to non-contact "{}"'.format(recipient_email))
        else:
            logger.error(str(ex))

        return False

    return 'messageId' in response.keys()

# print(str(send_transactional_email('Placeholder Drop Site Template', 'myemail@test.com')))
