from django.test import TestCase, Client
from django.urls import reverse

class MiscTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_faq_page(self):
        response = self.client.get(reverse('faq'))
        self.assertEqual(response.status_code, 200)

    def test_contact_page(self):
        response = self.client.get(reverse('contact'))
        self.assertEqual(response.status_code, 200)

    def test_shipping_info_page(self):
        response = self.client.get(reverse('shipping_info'))
        self.assertEqual(response.status_code, 200)

    def test_subscribe(self):
        response = self.client.post(reverse('subscribe'), {
            'email': 'test@example.com'
        })
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"success": True, "message": "Successfully subscribed! Check your email for confirmation."})
