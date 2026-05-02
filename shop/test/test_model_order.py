from django.test import TestCase
from django.contrib.auth.models import User
from ..models import Product, Order, OrderItem

class OrderModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.product = Product.objects.create(name='Item', price=500, category='men', stock=10)

    def test_order_tracking_number_generated(self):
        order = Order.objects.create(buyer=self.user)
        self.assertTrue(order.tracking_number)
        self.assertEqual(len(order.tracking_number), 8)

    def test_order_str_with_buyer(self):
        order = Order.objects.create(buyer=self.user)
        self.assertIn('testuser', str(order))

    def test_order_str_with_guest(self):
        order = Order.objects.create(email='guest@example.com')
        self.assertIn('guest@example.com', str(order))

    def test_get_total_amount(self):
        order = Order.objects.create(buyer=self.user)
        OrderItem.objects.create(order=order, product=self.product, quantity=2, price=500)
        self.assertEqual(order.get_total_amount(), 1000)

    def test_get_grand_total(self):
        order = Order.objects.create(buyer=self.user, delivery_fee=200)
        OrderItem.objects.create(order=order, product=self.product, quantity=1, price=500)
        self.assertEqual(order.get_grand_total(), 700)

class OrderItemModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser2', password='password')
        self.product = Product.objects.create(name='P1', price=100, category='men')
        self.order = Order.objects.create(buyer=self.user)
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=3,
            price=100,
            size='L'
        )

    def test_order_item_str(self):
        self.assertIn('3x P1 - Size L', str(self.order_item))

    def test_get_total(self):
        self.assertEqual(self.order_item.get_total(), 300)
