import hashlib
import hmac
import logging

import signrequest_client
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.http import HttpResponse
from django.urls import reverse
from mezzanine.core.request import current_request
from mezzanine.utils.email import send_mail_template

logger = logging.getLogger(__name__)

default_configuration = signrequest_client.Configuration()
default_configuration.api_key['Authorization'] = settings.SIGN_REQUEST_API_KEY
default_configuration.api_key_prefix['Authorization'] = 'Token'
signrequest_client.Configuration.set_default(default_configuration)

DOC_STATUS = {
    'converting': 'co',
    'new': 'ne',
    'sent': 'se',
    'viewed': 'vi',
    'signed': 'si',
    'downloaded': 'do',
    'signed_and_downloaded': 'sd',
    'cancelled': 'ca',
    'expired': 'xp',
    'declined': 'de',
    'error_converting': 'ec',
    'error_sending': 'es'
}


class DocSignedError(Exception):
    pass


def get_signrequest(user):
    api_instance = signrequest_client.DocumentsSearchApi()

    response = api_instance.documents_search_list(
        limit=1,
        q=user.email,
        # subdomain=settings.SIGN_REQUEST_SUBDOMAIN,
        # signer_emails=user.email,
    )

    if response.count == 0:
        return None

    doc = response.results[0]
    if doc.status in (DOC_STATUS['signed'], DOC_STATUS['signed_and_downloaded']):
        raise DocSignedError()

    if doc.status in (DOC_STATUS['converting'], DOC_STATUS['new'], DOC_STATUS['sent'], DOC_STATUS['viewed']):
        uuid = doc.uuid
        document = signrequest_client.DocumentsApi().documents_read(uuid)
        return document.signrequest.uuid


def send_sign_request(user, send_new=False):
    # check if we've already sent a SignRequest
    if not send_new:
        signrequest = get_signrequest(user)

        if signrequest:
            signrequest_client.SignrequestsApi().signrequests_resend_signrequest_email(signrequest)
            return

    # create a new one
    if user.profile.num_adults <= 4:
        template_uuid = settings.SIGN_REQUEST_TEMPLATES[user.profile.num_adults]
    else:
        template_uuid = settings.SIGN_REQUEST_TEMPLATES[4]

    redirect_url = current_request().build_absolute_uri(reverse("signrequest-success"))
    redirect_url_declined = current_request().build_absolute_uri(reverse("signrequest-declined"))

    data = signrequest_client.SignRequestQuickCreate(
        template='https://signrequest.com/api/v1/templates/{}/'.format(template_uuid),
        signers=[
            {
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
        ],
        from_email=settings.DEFAULT_FROM_EMAIL,
        redirect_url=redirect_url,
        redirect_url_declined=redirect_url_declined,
        who='o',
        send_reminders=True
    )

    api_instance = signrequest_client.SignrequestQuickCreateApi()
    api_instance.signrequest_quick_create_create(data)


def handle_webhook(event):
    # verify the event
    event_type = event['event_type']
    dig = hmac.new(
        msg='{event_time}{event_type}'.format(event_type=event_type, event_time=event['event_time']).encode(),
        key=settings.SIGN_REQUEST_API_KEY.encode(), digestmod=hashlib.sha256).hexdigest()

    if event['event_hash'] != dig:
        logger.warning('Invalid SignRequest event signature')
        return HttpResponse(status=400)

    if event['status'] != 'ok' or event_type in (
            'convert_error', 'sending_error', 'declined', 'cancelled', 'expired', 'signer_email_bounced'):
        send_error_email(event)
    elif event_type == 'signer_signed':
        User = get_user_model()
        email = event['signer']['email']

        try:
            user = User.objects.get(email=email)
            user.profile.signed_membership_agreement = True
            user.profile.save()
        except User.DoesNotExist:
            send_mail(
                'Member Store - Failed to find SignRequest user',
                'Failed to find a user with the email: {}'.format(email),
                settings.DEFAULT_FROM_EMAIL,
                [settings.DEFAULT_FROM_EMAIL],
            )

    return HttpResponse(status=200)


def send_error_email(event):
    send_mail_template(
        'FFCSA - SignRequest Error',
        "ffcsa_core/signrequest_error_email",
        settings.DEFAULT_FROM_EMAIL,
        settings.DEFAULT_FROM_EMAIL,
        context={
            'event': event
        },
        fail_silently=False,
    )
