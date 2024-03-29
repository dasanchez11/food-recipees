"""
Tests for the tags API.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Tag, Recipe

from recipe.serializers import TagSerializer


TAGS_URL = reverse("recipe:tag-list")


def detail_url(tag_id):
    """Create and return a tag detail url."""
    return reverse("recipe:tag-detail", args=[tag_id])


def create_user(email="user@example.com", password="testpass123"):
    """Create and return a user"""
    return get_user_model().objects.create_user(email, password)


def create_tag(user, **params):
    defaults = {
        "name": "Fish",
    }
    defaults.update(params)

    return Tag.objects.create(user=user, **defaults)


class PublicTagsApiTests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required for retrieving tags"""
        res = self.client.get(TAGS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsApiTests(TestCase):
    """Test Authenticated API requests."""

    def setUp(self):
        user = create_user()
        self.user = user
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        """Test retrieving a list of tags"""
        Tag.objects.create(user=self.user, name="New Tag")
        Tag.objects.create(user=self.user, name="Dessert")

        res = self.client.get(TAGS_URL)
        tags = Tag.objects.all().order_by("-name")
        serializer = TagSerializer(tags, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_tags_limited_to_user(self):
        """Test tags displayed are only asociated with user"""

        create_tag(user=self.user, name="A new Tag")
        create_tag(user=self.user, name="B new Tag")

        second_user = create_user(
            email="test2@example.com", password="password123"
        )

        create_tag(second_user)
        create_tag(second_user, name="name")

        res = self.client.get(TAGS_URL)
        tags = Tag.objects.all().order_by("-name").filter(user=self.user)
        serializer = TagSerializer(tags, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        self.assertEqual(res.data[0]["name"], serializer.data[0]["name"])
        self.assertEqual(res.data[0]["id"], serializer.data[0]["id"])

        self.assertEqual(res.data, serializer.data)

    def test_update_tag(self):
        """Test updating a tag."""
        tag = Tag.objects.create(user=self.user, name="After Dinner")

        payload = {"name": "Dessert"}
        url = detail_url(tag.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload["name"])

    def test_delete_tag(self):
        """Test Deleting a tag."""
        tag = Tag.objects.create(user=self.user, name="Diego")

        url = detail_url(tag.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        tags = Tag.objects.filter(user=self.user)
        self.assertFalse(tags.exists())

    def test_filter_tags_assigned_to_recipes(self):
        """Test listing tags to those assigned to recipes."""
        tag_1 = Tag.objects.create(user=self.user, name="Breakfast")
        tag_2 = Tag.objects.create(user=self.user, name="Lunch")
        reicpe = Recipe.objects.create(
            title="Green Eggs on Toast",
            time_minutes=5,
            price=Decimal("53.40"),
            user=self.user,
        )
        reicpe.tags.add(tag_1)

        res = self.client.get(TAGS_URL, {"assigned_only": 1})
        serializer_1 = TagSerializer(tag_1)
        serializer_2 = TagSerializer(tag_2)
        self.assertIn(serializer_1.data, res.data)
        self.assertNotIn(serializer_2.data, res.data)

    def test_filtered_tags_unique(self):
        """Test filtered tags return a unique list."""
        tag = Tag.objects.create(user=self.user, name="Eggs")
        Tag.objects.create(user=self.user, name="Lentils")
        reicpe = Recipe.objects.create(
            title="Sushi",
            time_minutes=5,
            price=Decimal("4.40"),
            user=self.user,
        )
        reicpe_2 = Recipe.objects.create(
            title="Herb eggs",
            time_minutes=25,
            price=Decimal("10.40"),
            user=self.user,
        )
        reicpe.tags.add(tag)
        reicpe_2.tags.add(tag)

        res = self.client.get(TAGS_URL, {"assigned_only": 1})
        self.assertEqual(len(res.data), 1)
