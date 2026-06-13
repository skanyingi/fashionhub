from django.test import TestCase, Client
from django.urls import reverse
from ..models import Product

class CartTestCase(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        self.client = Client()
        self.product = Product.objects.get(name='African Dress')
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
        out_of_stock_product = Product.objects.get(name='Out of Stock Bag')
        response = self.client.post(self.add_url, {
            'product_id': out_of_stock_product.id,
            'quantity': 1
        })
        self.assertEqual(response.status_code, 400)

    def test_cart_page(self):
        session = self.client.session
        session['cart'] = [{
            'product_id': str(self.product.id),
            'name': self.product.name,
            'price': 1500,
            'quantity': 2,
            'size': 'M'
        }]
        session.save()
        response = self.client.get(self.cart_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'African Dress')
        self.assertContains(response, '3000') 

    def test_update_cart(self):
        session = self.client.session
        session['cart'] = [{
            'name': self.product.name,
            'price': 1500,
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
            'price': 1500,
            'quantity': 1
        }]
        session.save()
        response = self.client.post(self.remove_url, {
            'name': self.product.name
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.client.session['cart']), 0)
