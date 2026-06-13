from django.test import TestCase
from ..models import Product, Review

class ProductModelTestCase(TestCase):
    fixtures = ['test_data.json']

    def test_product_str(self):
        product = Product.objects.get(name='African Dress')
        self.assertEqual(str(product), 'African Dress')

    def test_get_avg_rating_no_reviews(self):
        product = Product.objects.get(name='Men Leather Shoes')
        self.assertEqual(product.get_avg_rating(), 0)

    def test_get_avg_rating_with_reviews(self):
        product = Product.objects.get(name='African Dress')
        self.assertEqual(product.get_avg_rating(), 5.0)

    def test_get_review_count(self):
        product = Product.objects.get(name='African Dress')
        self.assertEqual(product.get_review_count(), 1)

class ReviewModelTestCase(TestCase):
    fixtures = ['test_data.json']

    def test_review_str(self):
        review = Review.objects.get(buyer__username='testuser')
        self.assertEqual(str(review), 'Review by testuser for African Dress')
