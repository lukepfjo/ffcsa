from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

from ffcsa.core import sendinblue
from ffcsa.shop.models import Order


class Command(BaseCommand):
    help = 'Add/Update all contacts in SIB'

    def handle(self, *args, **options):
        two_months_date = (datetime.now() - timedelta(days=60)).date()
        thirty_days = (datetime.now() - timedelta(days=30)).date()

        for user in get_user_model().objects.filter(is_active=True):
            # active if they have a subscription, or have signed up in the last 30 days, or have made an order
            # in the last 60 days (pay-in-advance members don't have a subscription)
            is_active = bool(user.profile.stripe_subscription_id) or user.date_joined.date() >= thirty_days or \
                        Order.objects.filter(user_id=user.id,
                                             time__gte=two_months_date).count() > 0

            lists_to_add = []
            lists_to_remove = []
            remove_member = False

            if is_active:
                lists_to_add.extend(['MEMBERS', 'WEEKLY_REMINDER'])
                lists_to_remove.extend(['PROSPECTIVE_MEMBERS', 'FORMER_MEMBERS'])
                if user.profile.weekly_emails:
                    lists_to_add.append('WEEKLY_NEWSLETTER')
            else:
                remove_member = True

            sendinblue.update_or_add_user(user, lists_to_add, lists_to_remove, remove_member=remove_member)
