from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from ..models import Product, Order, OrderItem, Transaction
import json
from shop.models import Transaction

class CheckoutIntegrationTestCase(TestCase):
    fixtures = ['test_data.json']

    def test_shopping_to_payment_flow(self):
        """Test Product -> Cart -> Shipping -> Payment flow"""
        user = User.objects.get(username='testuser')
        product = Product.objects.get(name='African Dress')
        order = Order.objects.get(tracking_number='TRACK123')
        
        self.client = Client()
        self.client.force_login(user)

        # Simulate adding items to cart
        session = self.client.session
        session['cart'] = [{
            'name': product.name,
            'price': 1500,
            'quantity': 2,
            'size': 'M'
        }]
        session.save()
        
        # View Cart and check total
        response = self.client.get(reverse('cart'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '3000') # 1500 * 2

        # Simulate Payment Callback      
        callback_data = {
            "Body": {
                "stkCallback": {
                    "CheckoutRequestID": "REQ123",
                    "ResultCode": 0,
                    "CallbackMetadata": {
                        "Item": [{"Name": "MpesaReceiptNumber", "Value": "R_SUCCESS"}]
                    }
                }
            }
        }
        self.client.post(
            reverse('mpesa_callback'),
            data=json.dumps(callback_data),
            content_type='application/json'
        )
        
        order.refresh_from_db() # Refreshing to see the updated status
        
        # Verify Order is PAID and Stock is Decremented
        self.assertEqual(order.status, 'PAID')
        
        # Transaction record
        transaction = Transaction.objects.filter(order=order).first()
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.mpesa_receipt_number, 'R_SUCCESS')
        self.assertEqual(transaction.status, 'SUCCESS')
