from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from ..models import Product, Order, OrderItem, Transaction
import json

class OrderTestCase(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(username='testuser')
        self.order = Order.objects.get(tracking_number='TRACK123')

    def test_order_history(self):
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('order_history'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.order.tracking_number)

    def test_update_shipping(self):
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.post(reverse('update_shipping'), {
            'location': 'Nakuru',
            'address': '456 Avenue',
            'phone': '0787654321'
        })
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.location, 'Nakuru')

    def test_track_order(self):
        response = self.client.post(reverse('track_order'), {
            'tracking_number': self.order.tracking_number
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.order.tracking_number)

    def test_delete_pending_order(self):
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.post(reverse('delete_pending_order', args=[self.order.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Order.objects.filter(id=self.order.id).exists())

    def test_mpesa_callback_success(self):
        Transaction.objects.create(order=self.order, checkout_request_id="REQ_CALLBACK_TEST", amount=1500, status='PENDING')
        
        callback_data = {
            "Body": {
                "stkCallback": {
                    "CheckoutRequestID": "REQ_CALLBACK_TEST",
                    "ResultCode": 0,
                    "ResultDesc": "Success",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "MpesaReceiptNumber", "Value": "R54321"}
                        ]
                    }
                }
            }
        }
        response = self.client.post(
            reverse('mpesa_callback'),
            data=json.dumps(callback_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'PAID')
        
        # Verify transaction updated
        transaction = Transaction.objects.get(checkout_request_id="REQ_CALLBACK_TEST")
        self.assertEqual(transaction.status, 'SUCCESS')
        self.assertEqual(transaction.mpesa_receipt_number, 'R54321')
