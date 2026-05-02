from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

class AuthTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.index_url = reverse('index')
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpassword123',
            'confirm_password': 'testpassword123'
        }

    def test_register_page_load(self):
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shop/register.html')

    def test_register_success(self):
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['HX-Redirect'], '/login')
        self.assertTrue(User.objects.filter(username='testuser').exists())

    def test_register_password_mismatch(self):
        data = self.user_data.copy()
        data['confirm_password'] = 'wrongpassword'
        response = self.client.post(self.register_url, data)
        self.assertContains(response, 'Passwords do not match')

    def test_register_duplicate_username(self):
        User.objects.create_user(username='testuser', password='password')
        response = self.client.post(self.register_url, self.user_data)
        self.assertContains(response, 'Username already taken')

    def test_login_page_load(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shop/login.html')

    def test_login_success(self):
        User.objects.create_user(username='testuser', password='testpassword123')
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'testpassword123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['HX-Redirect'], self.index_url)

    def test_login_invalid_username(self):
        response = self.client.post(self.login_url, {
            'username': 'nonexistent',
            'password': 'password'
        })
        self.assertContains(response, 'Invalid username')

    def test_login_invalid_password(self):
        User.objects.create_user(username='testuser', password='testpassword123')
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertContains(response, 'Invalid password')

    def test_logout(self):
        User.objects.create_user(username='testuser', password='testpassword123')
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(self.logout_url)
        self.assertRedirects(response, self.index_url)
