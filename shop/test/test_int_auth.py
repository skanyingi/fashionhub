from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

class AuthTestCase(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        self.client = Client()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.index_url = reverse('index')
        self.user_data = {
            'username': 'newuser',
            'email': 'new@test.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }

    def test_register_page_load(self):
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shop/register.html')

    def test_register_success(self):
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['HX-Redirect'], '/login')
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_register_password_mismatch(self):
        data = self.user_data.copy()
        data['confirm_password'] = 'wrongpassword'
        response = self.client.post(self.register_url, data)
        self.assertContains(response, 'Passwords do not match')

    def test_register_duplicate_username(self):
        # 'testuser' already exists in fixture
        data = self.user_data.copy()
        data['username'] = 'testuser'
        response = self.client.post(self.register_url, data)
        self.assertContains(response, 'Username already taken')

    def test_login_page_load(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shop/login.html')

    def test_login_success(self):
        # Pass '?next=index' to ensure the 'next' logic triggers in your view
        response = self.client.post(self.login_url + '?next=index', {
            'username': 'testuser',
            'password': 'testpassword123'
        })
        # print("Response Headers:", response.headers)
        self.assertEqual(response.status_code, 200)
        # The view redirects to 'index' which resolves to '/'
        self.assertEqual(response.get('HX-Redirect'), '/')

    def test_login_invalid_username(self):
        response = self.client.post(self.login_url, {
            'username': 'nonexistent',
            'password': 'password'
        })
        self.assertContains(response, 'Invalid username')

    def test_login_invalid_password(self):
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertContains(response, 'Invalid password')

    def test_logout(self):
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(self.logout_url)
        self.assertRedirects(response, self.index_url)
