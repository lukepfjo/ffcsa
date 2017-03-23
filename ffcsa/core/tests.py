from cartridge.shop.models import Cart, ProductVariation, Order, CartItem
from django.test import TestCase
from django.test import tag
from django.utils.timezone import now

from ffcsa.core import cron


@tag('integration')
class CloseOrderJobTests(TestCase):
    fixtures = ["users", "product"]

    def setUp(self):
        cart_1 = Cart.objects.create(last_updated=now(), user_id=1)
        cart_2 = Cart.objects.create(last_updated=now(), user_id=2)

        product = ProductVariation.objects.get(id=1)

        cart_1.add_item(product, 1)
        cart_2.add_item(product, 5)

    def test_orders_created_from_carts_and_carts_cleared(self):
        cron.close_order_job()

        orders = Order.objects.all()

        self.assertEqual(2, orders.count(), "wrong number of orders created from cart objects")

        order_1 = orders.filter(user_id=1).first()
        self.assertEqual(1, order_1.items.count())
        self.assertEqual(1, order_1.items.first().quantity)

        order_2 = orders.filter(user_id=2).first()
        self.assertEqual(1, order_2.items.count())
        self.assertEqual(5, order_2.items.first().quantity)

        for cart in Cart.objects.all():
            self.assertEqual(0, cart.items.count())

        self.assertEqual(0, CartItem.objects.count())
