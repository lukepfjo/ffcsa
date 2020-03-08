import datetime
import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management import BaseCommand

from ffcsa.shop.invoice import generate_invoices
from ffcsa.shop.models import Order
from ffcsa.shop.reports import generate_weekly_order_reports, send_order_to_vendor

# TODO :: logger isn't used in this file
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Generates and sends all reports for today's orders
    This is meant to be run as a cron job
    """
    help = 'Generate orders and reports for the weekly order'

    def add_arguments(self, parser):
        parser.add_argument('--send-orders', action='store_true', help='Send orders to vendors')
        parser.add_argument(
            '--date',
            action='store',
            type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d').date(),
            default=datetime.date.today(),
            help="Send orders to vendors"
        )

    def handle(self, *args, **options):
        date = options['date']

        try:
            vendor_orders, reports = generate_weekly_order_reports(date)

            if options['send_orders']:
                for vo in vendor_orders:
                    send_order_to_vendor(vo.order.write_pdf(), vo.vendor, vo.vendor_title, date)

            orders = Order.objects.filter(time__date=date)

            invoice_pages = []
            market_invoice_pages = []

            for invoice, order in generate_invoices(orders):
                # points to Items Ordered header
                # Lets rename to lastname
                bookmark = list(invoice.pages[0].bookmarks[0])
                bookmark[1] = order.billing_detail_last_name + " Invoice"
                invoice.pages[0].bookmarks[0] = tuple(bookmark)
                invoice_pages.extend(invoice.pages)

            # workaround for https://github.com/Kozea/WeasyPrint/issues/990
            for invoice, order in generate_invoices(orders):
                if order.drop_site in settings.MARKET_CHECKLISTS:
                    # points to Items Ordered header
                    # Lets rename to lastname
                    bookmark = list(invoice.pages[0].bookmarks[0])
                    bookmark[1] = order.billing_detail_last_name + " Market Invoice"
                    invoice.pages[0].bookmarks[0] = tuple(bookmark)
                    market_invoice_pages.extend(invoice.pages)

            doc = reports.copy(market_invoice_pages + reports.pages + invoice_pages)  # uses the metadata from reports

            # with tempfile.NamedTemporaryFile(
            #         delete=False, dir="app-messages", suffix='.pdf') as tmp:
            #     tmp.write(doc.write_pdf())
            #
            #     # Reset file pointer
            #     tmp.seek(0)

            msg = EmailMessage("Weekly Order Files - {}".format(date), "Weekly Order Files are attached.",
                               settings.EMAIL_HOST_USER, (settings.EMAIL_HOST_USER,))
            msg.attach("ffcsa_weekly_orders_{}.pdf".format(date), doc.write_pdf(), mimetype='application/pdf')
            msg.send()
        except Exception as e:
            EmailMessage("URGENT - Failed to send_weekly_orders", "Need to investigate asap.",
                         settings.EMAIL_HOST_USER, (settings.ADMINS[0][1],))
            raise e
