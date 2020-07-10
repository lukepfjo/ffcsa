from django.core.mail import send_mail
from django.db import connection
from mezzanine.conf import settings
from django.core.management import BaseCommand
from datetime import date, timedelta


class Command(BaseCommand):
    """
    """
    help = 'Get the current outstanding balances as of yesterday'

    def handle(self, *args, **options):
        yesterday = date.today() - timedelta(days=1)

        with connection.cursor() as cursor:
            query = """
                select (
                    select sum(amount) 
                    from ffcsa_core_payment 
                    where user_id <> 1 and date <= '{}'
                ) - (
                    select sum(total) 
                    from shop_order 
                    where date(time) >= '2017-12-01' and date(time) <= '{}' and user_id <> 1
                )""".format(yesterday, yesterday)
            cursor.execute(query)
            outstanding_balances = cursor.fetchall()[0][0]

        msg = "Outstanding member balances at the end of {}: ${}".format(yesterday, outstanding_balances)

        print(msg)
        send_mail(
            'Outstanding member balances',
            msg,
            settings.DEFAULT_FROM_EMAIL,
            [settings.DEFAULT_FROM_EMAIL],
            fail_silently=False,
        )
