import json

import requests

if __name__ == '__main__':
    from ffcsa.ffcsa import settings
    print('sendinblue.py :: loading settings.py directly')
else:
    from django.conf import settings

from django.utils.html import escape


_API_KEY = settings.SENDINBLUE_API_KEY
if _API_KEY is None:
    raise Exception('SENDINBLUE_API_KEY is not defined in local_settings.py')

_DEFAULT_HEADERS = {
    'accept': 'application/json',
    'content-type': 'application/json',
    'api-key': _API_KEY
}

_BASE_ENDPOINT = 'https://api.sendinblue.com/v3/'


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
            raise Exception('Sendinblue internal server error: HTTP {}'.format(response.status_code))

    try:
        return response.json()
    except json.decoder.JSONDecodeError:
        return response.text


def _initialize_drop_site_lists():
    # Create a dictionary of {drop_site_name: id} of the SIB drop site mailing lists
    # If drop sites in settings.py do not have corresponding lists on SIB, this will create them

    existing_lists = send_request('contacts/lists')
    drop_site_ids = {_list['name'].replace('Dropsite - ', ''): _list['id']
                     for _list in existing_lists['lists']
                     if _list['name'].startswith('Dropsite')}

    # Get the names of the drop_sites from settings.py and diff them with the folders on SIB
    missing_on_sib = [d[0] for d in settings.DROP_SITE_CHOICES if d[0] not in drop_site_ids.keys()]

    if len(missing_on_sib) > 0:
        folders = send_request('contacts/folders')['folders']
        drop_site_folder = [f['id'] for f in folders if f['name'] == settings.SENDINBLUE_DROP_SITE_FOLDER][0]

        for missing_drop_site in missing_on_sib:
            list_name = 'Dropsite - {}'.format(missing_drop_site)
            response = send_request('contacts/lists', method='POST',
                                    data={'name': list_name, 'folderId': drop_site_folder})
            drop_site_ids[missing_drop_site] = response['id']

    return drop_site_ids

_DROP_SITE_IDS = _initialize_drop_site_lists()


def _format_phone_number(phone_number):
    # Returns formatted phone number on success, False on failure

    for char in (' ', '-', '(', ')'):
        phone_number = phone_number.replace(char, '')

    if 0 < len(phone_number) < 10:
        return False

    # Lacking country code; assume US
    elif len(phone_number) == 10:
        return '+1' + phone_number

    # SIB requires a leading +
    elif len(phone_number) == 11:
        return '+' + phone_number


def add_new_user(email, first_name, last_name, drop_site, sms=None):
    """
    Add a new user to SIB. Adds user to the Weekly Newsletter, Weekly Reminder, Members, and provided drop site list

    @param email: Email of user to be added
    @param first_name: User's first name
    @param last_name: User's last name
    @param drop_site: Drop site name, ex: 'Hollywood'
    @param sms: User's cellphone number, not required

    @return: (True, '') on success, (False, '<some error message>') on failure
    """

    if drop_site not in (_[0] for _ in settings.DROP_SITE_CHOICES):
        return False, 'Drop site {} does not exist in settings.DROP_SITE_CHOICES'.format(drop_site)

    drop_site_list_id = _DROP_SITE_IDS[drop_site]

    sms = _format_phone_number(sms) if sms is not None else None
    if sms is False:
        return False, '{} is an invalid phone number'.format(escape(sms))

    body = {
        'updateEnabled': False,
        'email': email,
        'attributes': {
            'FIRSTNAME': first_name,
            'LASTNAME': last_name,
        },
        'listIds': [
            drop_site_list_id,
            settings.SENDINBLUE_LISTS['WEEKLY_NEWSLETTER'],
            settings.SENDINBLUE_LISTS['WEEKLY_REMINDER'],
            settings.SENDINBLUE_LISTS['MEMBERS']
        ]
    }

    if sms is not None:
        body['attributes']['sms'] = sms

    try:
        send_request('contacts', 'POST', data=body)

    except Exception as ex:
        if 'Contact already exist' in str(ex):
            return False, 'User already exists'
        raise ex

    return True, ''
