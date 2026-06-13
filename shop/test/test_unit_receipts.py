from django.test import TestCase
from ..models import Order, Receipt, Report

class ReceiptModelTestCase(TestCase):
    fixtures = ['test_data.json']

    def test_receipt_number_generation(self):

        receipt = Receipt.objects.get(pk=1)
        self.assertEqual(receipt.receipt_number, 'RCP-UNIQUE-999')

    def test_receipt_str(self):
        receipt = Receipt.objects.get(pk=1)
        self.assertEqual(str(receipt), 'Receipt RCP-UNIQUE-999')

class ReportModelTestCase(TestCase):
    fixtures = ['test_data.json']

    def test_report_creation_and_str(self):
        report = Report.objects.get(report_type='sales')
        self.assertIn('Sales Report', str(report))
        self.assertEqual(report.title, 'Sales Report')
