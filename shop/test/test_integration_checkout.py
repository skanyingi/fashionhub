from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from ..models import Product, Order, OrderItem
import json

class CheckoutIntegrationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.product = Product.objects.create(
            name='Test Shoe',
            price=2000,
            category='women',
            stock=10
        )

    def test_shopping_to_payment_flow(self):
        """Test Product -> Cart -> Shipping -> Payment flow"""
        # 0. Login first (required by update_shipping and stk_push)
        user = User.objects.create_user(username='checkoutuser', password='password')
        self.client.login(username='checkoutuser', password='password')

        # 1. Add to cart
        self.client.post(reverse('add_to_cart'), {
            'product_id': self.product.id,
            'quantity': 2,
            'size': '38'
        })
        
        # 2. View Cart and check total
        response = self.client.get(reverse('cart'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '4000') # 2000 * 2

        # 3. Update Shipping
        response = self.client.post(reverse('update_shipping'), {
            'location': 'Nairobi',
            'address': 'Moi Avenue',
            'phone': '0700000000',
            'email': 'user@test.com'
        })
        self.assertEqual(response.status_code, 200)
        
        # Get the order created for the user
        order = Order.objects.filter(buyer=user).first()
        order.checkout_request_id = 'REQ123' # Simulate STK push request ID
        order.save()

        # 4. Simulate M-Pesa Callback
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

        # 5. Verify Order is PAID and Stock is Decremented
        order.refresh_from_db()
        self.assertEqual(order.status, 'PAID')
        self.assertEqual(order.mpesa_receipt, 'R_SUCCESS')
        
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8) # 10 - 2
