"""
Tests For Models
"""


from django.test import TestCase
from django.contrib.auth import get_user_model


class ModelTests(TestCase):
    """Test Models"""

    def test_create_user_with_email_successful(self):
        """Test creating user when email is susccesful"""
        email = "test@example.com"
        password = "passoword"

        user = get_user_model().objects.model(email=email, password=password)

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))
