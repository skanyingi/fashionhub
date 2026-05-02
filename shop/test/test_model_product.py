from django.test import TestCase
from ..models import Product, Review

class ProductModelTestCase(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name='Test Product',
            price=1000,
            category='women',
            subcategory='shoes',
            stock=10
        )

    def test_product_str(self):
        self.assertEqual(str(self.product), 'Test Product')

    def test_get_avg_rating_no_reviews(self):
        self.assertEqual(self.product.get_avg_rating(), 0)

    def test_get_avg_rating_with_reviews(self):
        Review.objects.create(product=self.product, name='User 1', rating=4, comment='Good')
        Review.objects.create(product=self.product, name='User 2', rating=5, comment='Great')
        self.assertEqual(self.product.get_avg_rating(), 4.5)

    def test_get_review_count(self):
        Review.objects.create(product=self.product, name='User 1', rating=4, comment='Good')
        self.assertEqual(self.product.get_review_count(), 1)

class ReviewModelTestCase(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name='Test Product',
            price=1000,
            category='women'
        )
        self.review = Review.objects.create(
            product=self.product,
            name='John Doe',
            rating=5,
            comment='Excellent'
        )

    def test_review_str(self):
        self.assertEqual(str(self.review), 'Review by John Doe for Test Product')
