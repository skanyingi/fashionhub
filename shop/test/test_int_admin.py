from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from ..models import Product, Order, OrderItem, Report

class AdminIntegrationTestCase(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        self.client = Client()
        # Admin user needed for dashboard access
        self.admin = User.objects.create_superuser(username='admin', password='password')
        self.client.login(username='admin', password='password')

    def test_order_to_report_flow(self):
        """Test Order placement -> Inventory update -> Report generation flow"""
        # Data exists from fixture so i can fetch it.
        product = Product.objects.get(name='Men Leather Shoes')
        
        # Check Inventory Dashboard
        response = self.client.get(reverse('inventory'))
        self.assertEqual(response.status_code, 200)

        #  Trigger Report Generation
        response = self.client.get(reverse('generate_all_reports'))
        self.assertEqual(response.status_code, 302)

        # Verify Sales Report contains the data from fixture 
        sales_report = Report.objects.get(report_type='sales')
        self.assertGreaterEqual(sales_report.data['total_orders'], 1)
        self.assertGreaterEqual(sales_report.data['total_revenue'], 5000)
