import csv

from django.http import HttpResponse


def export_price_list(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="price_list.csv"'

    writer = csv.writer(response)
    writer.writerow(
        ['Product', 'Vendor', 'Available', 'Vendor Price', 'Member Price', '% Margin'])

    for product in queryset.order_by('variations__vendor', 'category', 'title'):
        row = [
            product.title,
            product.variations.first().vendor,
            product.available,
            product.vendor_price,
            product.unit_price
        ]

        if product.vendor_price and product.unit_price:
            row.append(
                ((product.unit_price - product.vendor_price) /
                 product.unit_price * 100).quantize(0)
            )
        else:
            row.append("")

        writer.writerow(row)

    return response
