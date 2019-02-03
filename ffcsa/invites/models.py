from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
from django.db import models
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType
from django.utils.crypto import get_random_string

AUTH_USER_MODEL = settings.AUTH_USER_MODEL


class InviteCodeIsOutOfDate(Exception):
    pass


class InviteCodeInvalidEmail(Exception):
    pass


def get_code_length():
    try:
        n = int(settings.INVITE_CODE_LENGTH)
    except (AttributeError, ValueError, TypeError):
        n = 9
    if n < 6:
        raise Exception("INVITE_CODE_LENGTH must be at least 3")
    if n > 30:
        raise Exception("INVITE_CODE_LENGTH must be at most 30")
    return n


class InvitationCodeManager(models.Manager):
    def create_invite_code(
            self, email, site=None, name=None, creator=None, drop_site=None, non_subscribing_member=False
    ):
        chars = 'ABCDEFGHJKMPQRSTUVWXYZ'
        nums = '23456789'
        site = site or Site.objects.get_current()
        N = get_code_length()
        while True:
            key = str(site.id) + '-'
            key += get_random_string(N - 3, chars) + get_random_string(3, nums)
            if not self.filter(site=site, key=key).exists():
                break
        code = self.model(
            key=key, site=site, registered_to=email, registered_name=name,
            created_by=creator, drop_site=drop_site, non_subscribing_member=non_subscribing_member
        )
        code.save()
        return code

    def get_code_from_key_if_valid(self, key, email=None, site=None):
        N = get_code_length()
        # no point in hitting the database if the code is the wrong format
        if not key or len(key) != N or not email:
            return
        top, tail = key[:-3], key[-3:]
        if (set('01') & set(tail)) | (set('ILN1234567890') & set(top)):
            return
        try:
            int(tail)
        except ValueError:
            return
        site = site or Site.objects.get_current()
        key = str(site.id) + '-' + key
        try:
            code = self.get(site=site, key=key)
        except:
            return
        if email and email != code.registered_to:
            raise InviteCodeInvalidEmail
        if code.expired:
            code.delete()
            raise InviteCodeIsOutOfDate

        return code


def get_default_site():
    return Site.objects.get(id=1)


def get_default_user():
    return get_user_model().objects.get(id=1)


class InvitationCode(models.Model):
    site = models.ForeignKey(Site, related_name="invite_codes", default=get_default_site)
    created_date = models.DateTimeField(
        editable=False, blank=True, default=timezone.now
    )
    created_by = models.ForeignKey(AUTH_USER_MODEL, blank=True, null=True,
                                   default=get_default_user)
    registered_to = models.EmailField('email', blank=False)
    registered_name = models.CharField(
        'name', max_length=70, blank=True, null=True
    )
    drop_site = models.CharField("Drop Site", blank=True, max_length=255)
    non_subscribing_member = models.BooleanField(default=False,
                                                 help_text="Non-subscribing members are allowed to make payments to their ffcsa account w/o having a monthly subscription")
    key = models.CharField(
        max_length=30, blank=True, null=True, editable=False
    )
    objects = InvitationCodeManager()

    class Meta:
        unique_together = ('site', 'key')

    def __repr__(self):
        return "<InvitationCode: %s>" % self.registered_to

    @property
    def short_key(self):
        if self.key:
            return self.key.rpartition('-')[2]

    def save(self, *args, **kwargs):
        if not hasattr(self, 'site') or not self.site:
            self.site_id = settings.SITE_ID
        super(InvitationCode, self).save(*args, **kwargs)

    @property
    def expired(self):
        now = timezone.now()
        try:
            usage_window = int(settings.invite_code_usage_window)
        except (AttributeError, ValueError, TypeError):
            usage_window = 14
        delta = timedelta(usage_window)

        if (now - self.created_date) > delta:
            return True

        return False
