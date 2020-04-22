import pickle
import logging
import os.path

from django.conf import settings
from django.core.mail import send_mail
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/contacts']

creds = False

logger = logging.getLogger(__name__)


def authenticate():
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    global creds
    if not creds and os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error('Failed to authenticate with Google. Google API access will not work - ', e)
                return False
        else:
            return False

    return True


def people_service():
    if not creds and not authenticate():
        raise Exception("Failed to authenticate against google api.")

    return build('people', 'v1', credentials=creds)


def build_people_obj(user):
    memberships = [
        {"contactGroupMembership": {"contactGroupResourceName": settings.GOOGLE_GROUP_IDS['MEMBERS']}},
        {"contactGroupMembership": {"contactGroupResourceName": settings.GOOGLE_GROUP_IDS['MANAGED']}},
        {"contactGroupMembership": {"contactGroupResourceName": 'contactGroups/myContacts'}}
    ]
    if user.profile.weekly_emails:
        memberships.append({
            "contactGroupMembership": {"contactGroupResourceName": settings.GOOGLE_GROUP_IDS['NEWSLETTER']}
        })

    return {
        "emailAddresses": [{"value": user.email}],
        "names": [{
            "givenName": user.first_name,
            "familyName": user.last_name,
        }],
        "phoneNumbers": [{"value": user.profile.phone_number, "metadata": {"primary": True}},
                         {"value": user.profile.phone_number_2}],
        "memberships": memberships
    }


def add_contact(user):
    try:
        res = people_service().people().createContact(body=build_people_obj(user)).execute()
        user.profile.google_person_id = res['resourceName']
        user.profile.save()
        return True
    except Exception as e:
        logger.error('Failed to create google contact for user:', user, e)


def find_user(user_obj):
    familyName = user_obj['names'][0]['familyName']
    givenName = user_obj['names'][0]['givenName']
    try:
        service = people_service()
        res = service.people().connections().list(resourceName="people/me", pageSize=2000,
                                                  personFields="metadata,names,memberships").execute()
        while True:
            for person in res['connections']:
                if 'names' not in person:
                    continue
                for name in person['names']:
                    try:
                        if name['familyName'] == familyName and name['givenName'] == givenName:
                            return person
                    except KeyError:
                        pass

            if 'nextPageToken' not in res:
                return False

            res = service.connections().list(resourceName="people/me", pageSize=2000,
                                             requestSyncToken=res['nextPageToken'],
                                             personFields="metadata,names,memberships").execute()
    except Exception as e:
        pass


def get_user(resourceName):
    try:
        return people_service().people().get(resourceName=resourceName, personFields="metadata,memberships").execute()
    except Exception as e:
        return False


def update_contact(user):
    try:
        obj = build_people_obj(user)
        u = None
        if user.profile.google_person_id:
            u = get_user(user.profile.google_person_id)

        if not u:
            u = find_user(obj)
            # This can happen if the contact is deleted, modified outside of the member store
            if user.profile.google_person_id:
                user.profile.google_person_id = None

        if not u:
            logger.warning('Failed to update google contact, attempting to create contact for user:', user)
            if not add_contact(user):
                send_mail(
                    "Failed Google Authentication %s" % settings.SITE_TITLE,
                    "Failed to update google contact for user" + user.first_name + " " + user.last_name,
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.ACCOUNTS_APPROVAL_EMAILS],
                    fail_silently=True,
                )
            return

        if not user.profile.google_person_id:
            user.profile.google_person_id = u['resourceName']
            user.profile.save()

        # check if the user has any memberships that we don't manage. If se, keep those
        managed_memberships = settings.GOOGLE_GROUP_IDS.values()
        for membership in u.get('memberships', []):
            if 'contactGroupMembership' in membership and membership['contactGroupMembership'][
                'contactGroupResourceName'] not in managed_memberships:
                obj['memberships'].append(membership)

        update_fields = ",".join(obj.keys())
        obj['metadata'] = u['metadata']

        people_service().people().updateContact(resourceName=u['resourceName'], updatePersonFields=update_fields,
                                                body=obj).execute()
    except Exception as e:
        logger.error('Failed to update google contact for user:', user, e)
