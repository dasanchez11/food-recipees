"""
Tests for the ingredients API.
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase


from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient
from recipe.serializers import IngredientSerializer


INGREDIENTS_URL = reverse("recipe:ingredient-list")


def detail_url(ingredient_id):
    """Create and return an ingredient detail URL."""
    return reverse("recipe:ingredient-detail", args=[ingredient_id])


def create_user(email="user@example.com", password="testpass123"):
    """Create and return a user"""
    return get_user_model().objects.create_user(email, password)


def create_ingredient(user, **params):
    """Create and return a user"""
    defaults = {
        "name": "Fish",
    }
    defaults.update(params)
    return Ingredient.objects.create(user=user, **defaults)


class PublicIngredientsApiTests(TestCase):
    """Test Unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required for retrieving tags"""
        res = self.client.get(INGREDIENTS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsApiTests(TestCase):
    """Test Authenticated API requests."""

    def setUp(self):
        user = create_user()
        self.user = user
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients(self):
        """Test retrieving a list of ingredients"""
        create_ingredient(self.user)
        create_ingredient(self.user, name="Tomato")

        res = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by("-name")
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """Test retrieving a list of ingredients belongs to user"""
        create_ingredient(self.user)
        create_ingredient(self.user, name="Tomato")
        user2 = create_user("new@example.com", "password")

        create_ingredient(user2, name="Onion")
        create_ingredient(user2, name="Jam")

        res = self.client.get(INGREDIENTS_URL)
        total_ingredients = Ingredient.objects.all().order_by("-name")
        ingredients = total_ingredients.filter(user=self.user)
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(total_ingredients.count(), 4)
        self.assertEqual(res.data, serializer.data)

    def test_update_ingredient(self):
        """Test updating an ingredient"""
        ingredient = create_ingredient(self.user, name="Tomato")
        payload = {"name": "Onion"}
        url = detail_url(ingredient.id)

        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload["name"])

    def test_clear_ingredient(self):
        """Test clearing ingredient."""
        ingredient = create_ingredient(self.user, name="Tomato")
        ingredients = Ingredient.objects.all().filter(user=self.user)
        url = detail_url(ingredient.id)
        res = self.client.delete(url, format="json")

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertNotIn(ingredient, ingredients)
        self.assertEqual(ingredients.count(), 0)
