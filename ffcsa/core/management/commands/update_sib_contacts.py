from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

from ffcsa.core import sendinblue
from ffcsa.shop.models import Order


class Command(BaseCommand):
    help = 'Add/Update all contacts in SIB'

    def handle(self, *args, **options):
        two_months_date = (datetime.now() - timedelta(days=60)).date()

        for user in get_user_model().objects.filter(is_active=True):
            drop_site_list = sendinblue.HOME_DELIVERY_LIST if user.profile.home_delivery else user.profile.drop_site

            is_active = user.profile.stripe_subscription_id or Order.objects.filter(user=user,
                                                                                    time__gte=two_months_date).count() > 0

            lists_to_add = []
            lists_to_remove = []

            if is_active:
                lists_to_add.extend(['MEMBERS', 'WEEKLY_REMINDER'])
                lists_to_remove.extend(['PROSPECTIVE_MEMBERS', 'FORMER_MEMBERS'])
                if user.profile.weekly_emails:
                    lists_to_add.append('WEEKLY_NEWSLETTER')
            else:
                lists_to_remove.extend(['MEMBERS'])
                lists_to_add.extend((['FORMER_MEMBERS']))

            sendinblue.update_or_add_user(user.email, user.first_name, user.last_name, drop_site_list,
                                          user.profile.phone_number, lists_to_add, lists_to_remove)
