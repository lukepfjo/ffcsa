from decimal import Decimal
from django.db.models import Sum, Manager


class PaymentManager(Manager):
    def total_for_user(self, user):
        total = self \
            .filter(user=user, pending=False) \
            .aggregate(total=Sum('amount'))['total']

        if total is None:
            total = Decimal(0)

        return total
