"""
Tests For Models
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model

from core import models


def create_user(email="user@example.com", password="user"):
    """Create and return a new user"""
    return get_user_model().objects.create_user(email, password)


class ModelTests(TestCase):
    """Test Models"""

    def test_create_user_with_email_successful(self):
        """Test creating user when email is susccesful"""
        email = "test@example.com"
        password = "passoword"

        user = get_user_model().objects.create_user(
            email=email, password=password
        )

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_new_email_normalized(self):
        """Test Email is normalized for new users"""
        sample_emails = [
            ["test1@EXAMPLE.com", "test1@example.com"],
            ["Test2@EXAMPLE.com", "Test2@example.com"],
            ["TEST3@EXAMPLE.com", "TEST3@example.com"],
            ["test4@example.COM", "test4@example.com"],
        ]

        for email, expected in sample_emails:
            user = get_user_model().objects.create_user(email, "sample")
            self.assertEqual(user.email, expected)

    def test_new_user_without_email_raises_error(self):
        """Test creating Email empty raises errors"""
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user("", "sample")

    def test_create_superuser(self):
        """Test creating Super User"""
        email = "test@example.com"
        password = "passoword"
        user = get_user_model().objects.create_superuser(
            email=email, password=password
        )

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_create_recipe(self):
        """Test Creatingg a recipe is successfull"""
        user = get_user_model().objects.create_user(
            "test@example.com", "password"
        )
        recipe = models.Recipe.objects.create(
            user=user,
            title="sample recipe name",
            time_minutes=5,
            price=Decimal("5.50"),
            description="sampel recipe description",
        )

        self.assertEqual(str(recipe), recipe.title)

    def test_create_tag(self):
        """Test Creating a tag is successful"""

        user = create_user()
        tag = models.Tag.objects.create(user=user, name="Tag 1")
        self.assertEqual(str(tag), tag.name)
