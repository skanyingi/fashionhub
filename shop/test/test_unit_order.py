from django.test import TestCase
from django.contrib.auth.models import User
from ..models import Product, Order, OrderItem

class OrderModelTestCase(TestCase):
    fixtures = ['test_data.json']

    def test_order_tracking_number_generated(self):
        user = User.objects.get(username='testuser')
        order = Order.objects.create(buyer=user)
        self.assertTrue(order.tracking_number)
        self.assertEqual(len(order.tracking_number), 8)

    def test_order_str_with_buyer(self):
        order = Order.objects.get(tracking_number='TRACK123')
        self.assertIn('testuser', str(order))

    def test_order_str_with_guest(self):
        order = Order.objects.create(email='guest@example.com')
        self.assertIn('guest@example.com', str(order))

    def test_get_total_amount(self):
        order = Order.objects.get(tracking_number='TRACK123')
        self.assertEqual(order.get_total_amount(), 1500)

    def test_get_grand_total(self):
        order = Order.objects.get(tracking_number='TRACK456')
        # Total 5000 (from fixture) + 0 delivery = 5000
        self.assertEqual(order.get_grand_total(), 5000)

class OrderItemModelTestCase(TestCase):
    fixtures = ['test_data.json']

    def test_order_item_str(self):
        order_item = OrderItem.objects.get(pk=1)
        self.assertIn('1x African Dress - Size M', str(order_item))

    def test_get_total(self):
        order_item = OrderItem.objects.get(pk=1)
        self.assertEqual(order_item.get_total(), 1500)
