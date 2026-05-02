from django.test import TestCase, Client
from django.urls import reverse
from ..models import Product, Review

class ProductTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.p1 = Product.objects.create(
            name='Women Shoes',
            price=2000,
            category='women',
            subcategory='shoes',
            stock=10
        )
        self.p2 = Product.objects.create(
            name='Men Shirt',
            price=1500,
            category='men',
            subcategory='clothing',
            stock=5
        )

    def test_index_page(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shop/index.html')

    def test_women_page(self):
        response = self.client.get(reverse('women'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Women Shoes')
        self.assertNotContains(response, 'Men Shirt')

    def test_men_page(self):
        response = self.client.get(reverse('men'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Men Shirt')
        self.assertNotContains(response, 'Women Shoes')

    def test_search(self):
        response = self.client.get(reverse('search'), {'q': 'Shoes'})
        self.assertContains(response, 'Women Shoes')
        self.assertNotContains(response, 'Men Shirt')

    def test_product_detail(self):
        response = self.client.get(reverse('product_detail', args=[self.p1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Women Shoes')

    def test_submit_review(self):
        response = self.client.post(reverse('submit_review', args=[self.p1.id]), {
            'name': 'John Doe',
            'rating': 5,
            'comment': 'Great shoes!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Review.objects.filter(product=self.p1, name='John Doe').exists())

    def test_sorting_women(self):
        response = self.client.get(reverse('women'), {'sort': 'low-to-high'})
        # Should work fine, just checking status
        self.assertEqual(response.status_code, 200)

    def test_filtering_women(self):
        response = self.client.get(reverse('women'), {'sub': 'shoes'})
        self.assertContains(response, 'Women Shoes')
