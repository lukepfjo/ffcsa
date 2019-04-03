from django.contrib.auth import get_user_model
from django.core.management import BaseCommand
import stripe


class Command(BaseCommand):
    def handle(self, *args, **options):
        users = get_user_model().objects.get(is_active=True)

        for user in users:
            if user.profile.stripe_subscription_id and user.profile.payment_method == 'CC':
                subscription = stripe.Subscription.retrieve(user.profile.stripe_subscription_id)
                subscription.tax_percent = 0
                subscription.save()
