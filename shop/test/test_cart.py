from django.test import TestCase, Client
from django.urls import reverse
from ..models import Product

class CartTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.product = Product.objects.create(
            name='Test Product',
            price=1000,
            category='women',
            stock=10
        )
        self.add_url = reverse('add_to_cart')
        self.cart_url = reverse('cart')
        self.update_url = reverse('update_cart')
        self.remove_url = reverse('remove_item')

    def test_add_to_cart(self):
        response = self.client.post(self.add_url, {
            'product_id': self.product.id,
            'quantity': 1,
            'size': 'M'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.client.session['cart']), 1)

    def test_add_out_of_stock(self):
        self.product.stock = 0
        self.product.save()
        response = self.client.post(self.add_url, {
            'product_id': self.product.id,
            'quantity': 1
        })
        self.assertEqual(response.status_code, 400)

    def test_cart_page(self):
        session = self.client.session
        session['cart'] = [{
            'product_id': str(self.product.id),
            'name': self.product.name,
            'price': 1000,
            'quantity': 2,
            'size': 'M'
        }]
        session.save()
        response = self.client.get(self.cart_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')
        self.assertContains(response, '2000') # 1000 * 2

    def test_update_cart(self):
        session = self.client.session
        session['cart'] = [{
            'name': self.product.name,
            'price': 1000,
            'quantity': 1
        }]
        session.save()
        response = self.client.post(self.update_url, {
            'action': 'increase',
            'name': self.product.name
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session['cart'][0]['quantity'], 2)

    def test_remove_item(self):
        session = self.client.session
        session['cart'] = [{
            'name': self.product.name,
            'price': 1000,
            'quantity': 1
        }]
        session.save()
        response = self.client.post(self.remove_url, {
            'name': self.product.name
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.client.session['cart']), 0)
