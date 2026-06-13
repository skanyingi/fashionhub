from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from ..models import Product, Order, Report

class ReportTestCase(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(username='admin', password='password', email='admin@test.com')
        self.client.login(username='admin', password='password')

    def test_inventory_page(self):
        response = self.client.get(reverse('inventory'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shop/inventory.html')

    def test_reports_page(self):
        response = self.client.get(reverse('reports'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shop/reports.html')

    def test_generate_reports(self):
        # Trigger report generation
        response = self.client.get(reverse('generate_all_reports'))
        self.assertEqual(response.status_code, 302)
        # Sales report exists in fixture
        self.assertTrue(Report.objects.filter(report_type='sales').exists())
