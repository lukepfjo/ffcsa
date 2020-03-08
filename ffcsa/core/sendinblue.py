import json

import requests

from django.conf import settings
from django.utils.html import escape


_API_KEY = settings.SENDINBLUE_API_KEY
if _API_KEY is None:
    raise Exception('SENDINBLUE_API_KEY is not defined in local_settings.py')

_DEFAULT_HEADERS = {
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
    headers = {} if headers is None else headers
    headers.update(_DEFAULT_HEADERS)

    response = requests.request(method, endpoint, headers=headers, data=json.dumps(data), params=query)

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


def _populate_dropsite_lists():
    response = send_request('contacts/lists')
    return {_list['name'].replace('Dropsite - ', ''): _list['id']
            for _list in response['lists']
            if _list['name'].startswith('Dropsite')}

_DROPSITE_LISTS = _populate_dropsite_lists()


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


def add_new_user(email, firstname, lastname, dropsite, sms=None):
    """
    Add a new user to SIB. Adds user to the Weekly Newsletter, Weekly Reminder, Members, and provided dropsite list.

    @param email: Email of user to be added
    @param firstname: User's first name
    @param lastname: User's last name
    @param dropsite: Dropsite name, ex: 'Hollywood'
    @param sms: User's cellphone number, not required

    @return: (True, '') on success, (False, '<some error message>') on failure
    """

    dropsite = dropsite.capitalize()
    dropsite_list_id = _DROPSITE_LISTS.get(dropsite, None)
    if dropsite_list_id is None:
        raise Exception('Sendinblue error: Dropsite list "Dropsite - {}" does not exist'.format(dropsite))

    sms = _format_phone_number(sms) if sms is not None else None
    if sms is False:
        return False, '{} is an invalid phone number'.format(escape(sms))

    body = {
        'updateEnabled': False,
        'email': email,
        'attributes': {
            'FIRSTNAME': firstname,
            'LASTNAME': lastname,
        },
        'listIds': [
            dropsite_list_id,
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
