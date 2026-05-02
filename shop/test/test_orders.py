from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from ..models import Product, Order, OrderItem
import json

class OrderTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='buyer', password='password')
        self.product = Product.objects.create(name='Item', price=500, category='men', stock=20)
        self.order = Order.objects.create(buyer=self.user, status='PENDING')
        OrderItem.objects.create(order=self.order, product=self.product, quantity=2, price=500)

    def test_order_history(self):
        self.client.login(username='buyer', password='password')
        response = self.client.get(reverse('order_history'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.order.tracking_number)

    def test_update_shipping(self):
        self.client.login(username='buyer', password='password')
        response = self.client.post(reverse('update_shipping'), {
            'location': 'Nairobi',
            'address': '123 Street',
            'phone': '0712345678'
        })
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.location, 'Nairobi')

    def test_track_order(self):
        response = self.client.post(reverse('track_order'), {
            'tracking_number': self.order.tracking_number
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.order.tracking_number)

    def test_delete_pending_order(self):
        self.client.login(username='buyer', password='password')
        response = self.client.post(reverse('delete_pending_order', args=[self.order.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Order.objects.filter(id=self.order.id).exists())

    def test_mpesa_callback_success(self):
        # Simulate M-Pesa callback
        callback_data = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "123",
                    "CheckoutRequestID": "abc",
                    "ResultCode": 0,
                    "ResultDesc": "Success",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": 1000},
                            {"Name": "MpesaReceiptNumber", "Value": "R12345"}
                        ]
                    }
                }
            }
        }
        self.order.checkout_request_id = "abc"
        self.order.save()
        
        response = self.client.post(
            reverse('mpesa_callback'),
            data=json.dumps(callback_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'PAID')
        self.assertEqual(self.order.mpesa_receipt, 'R12345')
