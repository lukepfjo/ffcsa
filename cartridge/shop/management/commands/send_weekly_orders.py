from django.core.management import BaseCommand

from cartridge.shop.reports import generate_weekly_order_reports


class Command(BaseCommand):
    """
    Generates and sends all reports for today's orders
    This is meant to be run as a cron job
    """
    help = 'send'

    def handle(self, *args, **options):
        generate_weekly_order_reports()
