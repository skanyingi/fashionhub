from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from ..models import Review, ReviewHelpful

class ReviewHelpfulTestCase(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(username='testuser')
        self.review = Review.objects.get(pk=1)
        self.helpful_url = reverse('toggle_review_helpful', args=[self.review.id])

    def test_helpful_count_initial(self):
        """Verify initial helpful count from fixture"""
        self.assertEqual(self.review.get_helpful_count(), 1)

    def test_toggle_helpful_authenticated(self):
        """Test toggling helpful vote (authenticated)"""
        self.client.login(username='testuser', password='testpassword123')
        
        #  First toggle: should UNVOTE because fixture already has a vote for this user
        response = self.client.post(self.helpful_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.review.get_helpful_count(), 0)
        
        #  Second toggle: should VOTE back
        response = self.client.post(self.helpful_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.review.get_helpful_count(), 1)

    def test_helpful_requires_login(self):
        """Verify that voting redirects to login for unauthenticated users"""
        # toggle_review_helpful uses @login_required
        response = self.client.post(self.helpful_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.url)
