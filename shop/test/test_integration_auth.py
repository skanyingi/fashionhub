from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

class AuthIntegrationTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_full_auth_cycle(self):
        """Test Register -> Login -> Logout flow"""
        # 1. Register
        register_data = {
            'username': 'newuser',
            'email': 'new@test.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }
        response = self.client.post(reverse('register'), register_data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username='newuser').exists())

        # 2. Login
        response = self.client.post(reverse('login'), {
            'username': 'newuser',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 200)
        
        # Verify user is logged in by checking index page context or similar
        response = self.client.get(reverse('index'))
        self.assertEqual(response.context['user'].username, 'newuser')

        # 3. Logout
        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, reverse('index'))
        
        # Verify user is logged out
        response = self.client.get(reverse('index'))
        self.assertFalse(response.context['user'].is_authenticated)
