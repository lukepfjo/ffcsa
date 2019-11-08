from collections import namedtuple, OrderedDict
from itertools import groupby

from django.template.loader import get_template
from weasyprint import HTML

from cartridge.shop.models import Category

OrderInvoice = namedtuple('OrderInvoice', ['invoice', 'order'])


def generate_invoices(orders):
    from cartridge.shop.actions.order_actions import order_sort, keySort
    orders = list(orders)

    categories = Category.objects.exclude(slug='weekly-box')

    orders.sort(key=order_sort)

    for order in orders:
        context = {"order": order}
        context.update(order.details_as_dict())

        items = [i for i in order.items.all_grouped()]

        items.sort(key=keySort(categories))

        grouper = groupby(items, keySort(categories))
        grouped_items = OrderedDict()

        for k, g in grouper:
            k = int(k[0])
            if not k in grouped_items:
                grouped_items[k] = []
            grouped_items[k] += list(g)

        context['grouped_items'] = grouped_items
        context['details'] = [
            [("Name", order.billing_detail_first_name +
              " " + order.billing_detail_last_name)],
            [("Phone", order.billing_detail_phone),
             ("Alt. Phone", order.billing_detail_phone_2)],
        ]

        html = get_template("shop/order_packlist_pdf.html").render(context)

        yield OrderInvoice(HTML(string=html).render(), order)
