from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from ..models import Product, Review

class ProductTestCase(TestCase):
    fixtures = ['test_data.json']

    def test_index_page(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shop/index.html')

    def test_women_page(self):
        response = self.client.get(reverse('women'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'African Dress')
        self.assertNotContains(response, 'Men Leather Shoes')

    def test_men_page(self):
        response = self.client.get(reverse('men'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Men Leather Shoes')
        self.assertNotContains(response, 'African Dress')

    def test_search(self):
        response = self.client.get(reverse('search'), {'q': 'African'})
        self.assertContains(response, 'African Dress')
        self.assertNotContains(response, 'Men Leather Shoes')

    def test_product_detail(self):
        product = Product.objects.get(name='African Dress')
        response = self.client.get(reverse('product_detail', args=[product.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'African Dress')

    def test_submit_review(self):
        product = Product.objects.get(name='African Dress')
        user = User.objects.get(username='testuser')
        self.client.login(username='testuser', password='testpassword123')
        
        response = self.client.post(reverse('submit_review', args=[product.id]), {
            'rating': 5,
            'comment': 'Great product!'
        })
        self.assertEqual(response.status_code, 200)
        # Verify review linked to authenticated user
        self.assertTrue(Review.objects.filter(product=product, buyer=user).exists())

    def test_sorting_women(self):
        response = self.client.get(reverse('women'), {'sort': 'low-to-high'})
        self.assertEqual(response.status_code, 200)

    def test_filtering_women(self):
        response = self.client.get(reverse('women'), {'sub': 'clothing'})
        self.assertContains(response, 'African Dress')
