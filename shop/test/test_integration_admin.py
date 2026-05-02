from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from ..models import Product, Order, OrderItem, Report

class AdminIntegrationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(username='admin', password='password')
        self.client.login(username='admin', password='password')
        self.product = Product.objects.create(name='Widget', price=100, category='men', stock=50)

    def test_order_to_report_flow(self):
        """Test Order placement -> Inventory update -> Report generation flow"""
        # 1. Place a paid order
        order = Order.objects.create(status='PAID', delivery_fee=0)
        OrderItem.objects.create(order=order, product=self.product, quantity=5, price=100)
        
        # 2. Check Inventory Dashboard
        response = self.client.get(reverse('inventory'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '500') # Total revenue

        # 3. Trigger Report Generation
        response = self.client.get(reverse('generate_all_reports'))
        self.assertEqual(response.status_code, 302) # Redirects back to reports

        # 4. Verify Sales Report contains the new data
        sales_report = Report.objects.get(report_type='sales')
        self.assertEqual(sales_report.data['total_orders'], 1)
        self.assertEqual(sales_report.data['total_revenue'], 500)

        # 5. Check Product Detail for Review Integration
        self.client.post(reverse('submit_review', args=[self.product.id]), {
            'name': 'Critic',
            'rating': 5,
            'comment': 'Amazing'
        })
        
        # Re-generate reports to see review count update
        self.client.get(reverse('generate_all_reports'))
        prod_report = Report.objects.get(report_type='products')
        # Check if "Widget" is in the items list of the report
        widget_found = any(item['name'] == 'Widget' for item in prod_report.data['items'])
        self.assertTrue(widget_found)
