import csv
import io

from django.conf import settings
from django.db.models import F

from ffcsa.shop.reports import _get_market_checklist_qs


def generate_deliveries_csv(orders):
    """Generates a csv file with addresses and shipping_instruction for uploading into google maps"""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)

    writer.writerow(['Address', 'Last Name', 'Instructions'])

    for o in orders.order_by('shipping_detail_city', 'shipping_detail_street'):
        address = '{}, {}, {} {}'.format(o.shipping_detail_street, o.shipping_detail_city, o.shipping_detail_state,
                                         o.shipping_detail_postcode)
        writer.writerow([address, o.billing_detail_last_name, o.shipping_instructions])

    return output.getvalue()


def generate_deliveries_optimoroute_csv(date):
    """Generates a csv file with addresses and shipping_instruction for uploading into google maps"""
    drop_site = 'Home Delivery'
    day_of_week = date.isoweekday()

    annotations = {
        'last_name': F('billing_detail_last_name'),
        'first_name': F('billing_detail_first_name'),
        'email': F('billing_detail_email'),
        'phone': F('billing_detail_phone'),
        'shipping_street': F('shipping_detail_street'),
        'shipping_city': F('shipping_detail_city'),
        'shipping_state': F('shipping_detail_state'),
        'shipping_zip': F('shipping_detail_postcode'),
        'shipping_ins': F('shipping_instructions'),
    }
    qs, columns = _get_market_checklist_qs(date, drop_site, annotations)

    if day_of_week not in settings.DELIVERY_CSVS:
        return []

    file_settings = settings.DELIVERY_CSVS[day_of_week]

    # setup the default writer
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerow(
        ['Address', 'Name', 'Phone', 'Email', 'Notes', 'Duration', 'tw start', 'tw end', 'Boxes', 'Dairy', 'Meat',
         'Flowers', 'notifications'])

    writers = {'default': {
        'output': output,
        'writer': writer
    }}

    writers_by_zip = {}

    for file in file_settings:
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)
        writer.writerow(
            ['Address', 'Name', 'Phone', 'Email', 'Notes', 'Duration', 'tw start', 'tw end', 'Boxes', 'Dairy', 'Meat',
             'Flowers', 'notifications'])

        for d in file['standingDeliveries']:
            writer.writerow(d)

        writers[file['name']] = {
            'output': output,
            'writer': writer
        }

        for zip in file['zipCodes']:
            writers_by_zip[zip] = writer

    used_default = False
    for o in qs.values(*columns):
        if o['shipping_zip'] in writers_by_zip:
            writer = writers_by_zip[o['shipping_zip']]
        else:
            writer = writers['default']['writer']
            used_default = True

        address = '{}, {}, {} {}'.format(o['shipping_street'], o['shipping_city'], o['shipping_state'],
                                         o['shipping_zip'])
        name = '{}, {}'.format(o['last_name'], o['first_name'])
        writer.writerow(
            [address, name, o['phone'], o['email'], o['shipping_ins'], '4', '', '', o['Tote'], o['Dairy'], o['Meat'],
             o['Flowers'], 'email'])

    if not used_default:
        del writers['default']

    return [(name, d['output'].getvalue()) for name, d in writers.items()]
