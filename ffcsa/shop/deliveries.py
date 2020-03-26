import csv
import io


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
