from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

from ffcsa.core import sendinblue


class Command(BaseCommand):
    help = 'Add/Update all contacts in SIB'

    def handle(self, *args, **options):
        for user in get_user_model().objects.filter(active=True):
            drop_site_list = sendinblue.HOME_DELIVERY_LIST if user.profile.home_delivery else user.profile.drop_site

            weekly_email_lists = ['WEEKLY_NEWSLETTER', 'WEEKLY_REMINDER']
            lists_to_add = weekly_email_lists if user.profile.weekly_emails else None
            lists_to_remove = weekly_email_lists if not user.profile.weekly_emails else None

            sendinblue.update_or_add_user(user.email, user.first_name, user.last_name, drop_site_list,
                                          user.profile.phone_number, lists_to_add, lists_to_remove)
