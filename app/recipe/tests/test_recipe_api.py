"""
Tests for recipe APIs.
"""

from decimal import Decimal
import tempfile
import os

from PIL import Image


from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient

from recipe.serializers import RecipeSerializer, RecipeDetailSerializer


RECIPE_URL = reverse("recipe:recipe-list")


def detail_url(recipe_id):
    """Create and return a recipe detail URL."""
    return reverse("recipe:recipe-detail", args=[recipe_id])


def image_upload_url(recipe_id):
    """Create and return Uploaded an image."""
    return reverse("recipe:recipe-upload-image", args=[recipe_id])


def create_recipe(user, **params):
    """Create and return a sample recipe."""
    defaults = {
        "title": "Sample recipe title",
        "time_minutes": 22,
        "price": Decimal("10.50"),
        "description": "recipe description",
        "link": "https://example.com/recipe.pdf",
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


def create_user(**params):
    """Create and return new user."""
    return get_user_model().objects.create_user(**params)


class PublicRecipeAPITests(TestCase):
    """Test unauthenticated API requests"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call api"""

        res = self.client.get(RECIPE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeAPITests(TestCase):
    """Test authenticated API requests"""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email="user@example.com", password="password")

        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        create_recipe(self.user)
        create_recipe(self.user)

        res = self.client.get(RECIPE_URL)
        recipes = Recipe.objects.all().order_by("-id")
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_list_limited_to_user(self):
        """Test list of recipes is only for the current user"""

        create_recipe(self.user)
        create_recipe(self.user)

        second_user = create_user(
            email="test2@example.com", password="password123"
        )

        create_recipe(second_user)
        create_recipe(second_user)

        res = self.client.get(RECIPE_URL)
        recipes = Recipe.objects.all().order_by("-id").filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        """Test get recipe detail."""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        """Test creating a recipe."""

        payload = {
            "title": "sample title",
            "time_minutes": 30,
            "price": Decimal("7.99"),
        }

        res = self.client.post(RECIPE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data["id"])
        for key, value in payload.items():
            self.assertEqual(getattr(recipe, key), value)
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        """Test partial update for a recipe."""
        original_link = "https://example.com/recipe.pdf"
        recipe = create_recipe(
            user=self.user, title="sample title", link=original_link
        )

        payload = {"title": "new recipe title"}
        url = detail_url(recipe_id=recipe.id)
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(res.data["title"], payload["title"])
        self.assertEqual(res.data["link"], original_link)
        self.assertEqual(recipe.user, self.user)

        # def test_full_update(self):
        #     """Test full update for a recipe."""
        #     original_link = "https://example.com/recipe.pdf"
        #     recipe = create_recipe(
        #         user=self.user,
        #         title="sample title",
        #         link=original_link,
        #         description="Sample description",
        #     )

        #     payload = {
        #         "title": "new recipe title",
        #         "link": "new link",
        #         "description": "New Description",
        #         "time_minutes": 10,
        #         "price": Decimal(11.09),
        #     }
        #     url = detail_url(recipe.id)
        #     res = self.client.put(url, payload)

        #     self.assertEqual(res.status_code, status.HTTP_200_OK)
        #     recipe.refresh_from_db()

        #     for key, value in payload.values():
        #         self.assertAlmostEqual(getattr(payload, key), value)

        #     self.assertEqual(recipe.user, self.user)

    def test_create_recipe_with_new_tags(self):
        """Test creating recipe with new tags."""
        payload = {
            "title": "sample title",
            "time_minutes": 30,
            "price": Decimal("7.99"),
            "tags": [{"name": "Thai"}, {"name": "Dinner"}],
        }
        res = self.client.post(RECIPE_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)

        for tag in payload["tags"]:
            exists = recipe.tags.filter(
                user=self.user, name=tag["name"]
            ).exists()
            self.assertTrue(exists)

    def test_creating_recipe_with_existing_tags(self):
        """Test creating recipe with existing tags."""
        tag_colombian = Tag.objects.create(user=self.user, name="Colombian")
        payload = {
            "title": "sample title",
            "time_minutes": 30,
            "price": Decimal("7.99"),
            "tags": [{"name": "Colombian"}, {"name": "Dinner"}],
        }
        res = self.client.post(RECIPE_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_colombian, recipe.tags.all())
        for tag in payload["tags"]:
            exists = recipe.tags.filter(
                user=self.user, name=tag["name"]
            ).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        """Test creating a tag when updating a recipe"""
        recipe = create_recipe(user=self.user)

        payload = {"tags": [{"name": "Lunch"}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name="Lunch")
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assign_tag(self):
        """Test assigning an existing tag when updating a recipe."""
        tag_breakfast = Tag.objects.create(user=self.user, name="Breakfast")
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_breakfast)

        tag_lunch = Tag.objects.create(user=self.user, name="Lunch")
        payload = {"tags": [{"name": "Lunch"}]}

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_lunch, recipe.tags.all())
        self.assertNotIn(tag_breakfast, recipe.tags.all())

    def test_clear_recipe_tags(self):
        """Test clearing recipes tags."""
        tag = Tag.objects.create(user=self.user, name="Dessert")
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag)

        payload = {"tags": []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(tag, recipe.tags.all())
        self.assertEqual(recipe.tags.count(), 0)

    def test_creating_recipe_ingredient(self):
        """Test creating a recipe with new ingredients."""

        payload = {
            "title": "sample title",
            "time_minutes": 30,
            "price": Decimal("7.99"),
            "ingredients": [{"name": "Tomato"}, {"name": "Onions"}],
        }
        res = self.client.post(RECIPE_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)

        for ingredient in payload["ingredients"]:
            exists = recipe.ingredients.filter(
                user=self.user, name=ingredient["name"]
            ).exists()
            self.assertTrue(exists)

    def test_creating_ingredient_with_existing_tags(self):
        """Test creating recipe with existing ingredients."""
        ingredient_tomato = Ingredient.objects.create(
            user=self.user, name="tomato"
        )
        payload = {
            "title": "sample title",
            "time_minutes": 30,
            "price": Decimal("7.99"),
            "ingredients": [{"name": "tomato"}, {"name": "Onion"}],
        }
        res = self.client.post(RECIPE_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingredient_tomato, recipe.ingredients.all())
        for ingredient in payload["ingredients"]:
            exists = recipe.ingredients.filter(
                user=self.user, name=ingredient["name"]
            ).exists()
            self.assertTrue(exists)

    def test_create_ingredient_on_update(self):
        """Test creating an ingredient when updating a recipe"""
        recipe = create_recipe(user=self.user)

        payload = {"ingredients": [{"name": "Broccoli"}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_ingredient = Ingredient.objects.get(
            user=self.user, name="Broccoli"
        )
        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_update_recipe_assign_ingredient(self):
        """Test assigning an existing ingredient when updating a recipe."""
        ingredient_tomato = Ingredient.objects.create(
            user=self.user, name="tomato"
        )
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient_tomato)

        ingredient_onion = Ingredient.objects.create(
            user=self.user, name="Onion"
        )
        payload = {"ingredient": [{"name": "Onion"}]}

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient_tomato, recipe.ingredients.all())
        self.assertNotIn(ingredient_onion, recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        """Test clearing recipes ingredients."""
        ingredient = Ingredient.objects.create(user=self.user, name="Limes")
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)

        payload = {"ingredients": []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(ingredient, recipe.ingredients.all())
        self.assertEqual(recipe.ingredients.count(), 0)

    def test_filter_by_tags(self):
        """Test filtering recipes by tags"""
        recipe_1 = create_recipe(user=self.user, title="Thai Vegetable curry")
        recipe_2 = create_recipe(user=self.user, title="Sancocho")
        tag_1 = Tag.objects.create(user=self.user, name="Vegan")
        tag_2 = Tag.objects.create(user=self.user, name="Colombian")
        recipe_1.tags.add(tag_1)
        recipe_2.tags.add(tag_2)
        recipe_3 = create_recipe(user=self.user, title="Fish and chips")

        params = {"tags": f"{tag_1.id},{tag_2.id}"}
        res = self.client.get(RECIPE_URL, params)

        serializer_1 = RecipeSerializer(recipe_1)
        serializer_2 = RecipeSerializer(recipe_2)
        serializer_3 = RecipeSerializer(recipe_3)
        self.assertIn(serializer_1.data, res.data)
        self.assertIn(serializer_2.data, res.data)
        self.assertNotIn(serializer_3.data, res.data)

    def test_filter_by_ingredients(self):
        """Test filtering recipes by ingredients"""
        recipe_1 = create_recipe(user=self.user, title="Thai Vegetable curry")
        recipe_2 = create_recipe(user=self.user, title="Sancocho")
        ingredient_1 = Ingredient.objects.create(user=self.user, name="Curry")
        ingredient_2 = Ingredient.objects.create(user=self.user, name="Rice")
        recipe_1.ingredients.add(ingredient_1)
        recipe_2.ingredients.add(ingredient_2)
        recipe_3 = create_recipe(user=self.user, title="Fish and chips")

        params = {"ingredients": f"{ingredient_1.id},{ingredient_2.id}"}
        res = self.client.get(RECIPE_URL, params)

        serializer_1 = RecipeSerializer(recipe_1)
        serializer_2 = RecipeSerializer(recipe_2)
        serializer_3 = RecipeSerializer(recipe_3)
        self.assertIn(serializer_1.data, res.data)
        self.assertIn(serializer_2.data, res.data)
        self.assertNotIn(serializer_3.data, res.data)


class ImageUploadTests(TestCase):
    """Tests for image upload API."""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@example.con", "password"
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image(self):
        """test uploading an image to a reipe."""
        url = image_upload_url(self.recipe.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            img = Image.new("RGB", (10, 10))
            img.save(image_file, format="JPEG")
            image_file.seek(0)
            payload = {"image": image_file}
            res = self.client.post(url, payload, format="multipart")

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        """Test failing to upload an image"""
        url = image_upload_url(self.recipe.id)
        payload = {"image": "notanimage"}
        res = self.client.post(url, payload, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
