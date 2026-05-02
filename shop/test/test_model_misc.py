from django.test import TestCase
from ..models import Order, Receipt, Report

class ReceiptModelTestCase(TestCase):
    def setUp(self):
        self.order = Order.objects.create(tracking_number='TRACK123')

    def test_receipt_number_generation(self):
        receipt = Receipt.objects.create(order=self.order)
        self.assertEqual(receipt.receipt_number, 'RCP-TRACK123')

    def test_receipt_str(self):
        receipt = Receipt.objects.create(order=self.order)
        self.assertEqual(str(receipt), 'Receipt RCP-TRACK123')

class ReportModelTestCase(TestCase):
    def test_report_creation_and_str(self):
        report = Report.objects.create(
            report_type='sales',
            title='Monthly Sales',
            data={'total': 5000}
        )
        self.assertIn('Sales Report', str(report))
        self.assertEqual(report.data['total'], 5000)
