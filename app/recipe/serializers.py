"""
Serializers for recipe APIs
"""


from rest_framework import serializers

from core.models import Recipe, Tag, Ingredient


class IngredientSerializer(serializers.ModelSerializer):
    """Serializer for the ingredients."""

    class Meta:
        model = Ingredient
        fields = ["id", "name"]
        read_only_fields = ["id"]


class TagSerializer(serializers.ModelSerializer):
    """Serializer for tags"""

    class Meta:
        model = Tag
        fields = ["id", "name"]
        read_only_fields = ["id"]


class RecipeSerializer(serializers.ModelSerializer):
    """Serializer for recipes."""

    tags = TagSerializer(many=True, required=False)
    ingredients = IngredientSerializer(many=True, required=False)

    class Meta:
        model = Recipe
        fields = [
            "id",
            "title",
            "time_minutes",
            "price",
            "link",
            "tags",
            "ingredients",
        ]
        read_only_fields = ["id"]

    def _get_or_create_tag(self, tags, recipe):
        """Handle getting or creating tags as needed"""
        auth_user = self.context["request"].user
        for tag in tags:
            tag_object, created = Tag.objects.get_or_create(
                user=auth_user, **tag
            )
            recipe.tags.add(tag_object)

    def _get_or_create_ingredient(self, ingredients, recipe):
        """Handle getting or creating ingredients as needed"""
        auth_user = self.context["request"].user
        for ingredient in ingredients:
            ingredient_object, created = Ingredient.objects.get_or_create(
                user=auth_user, **ingredient
            )
            recipe.ingredients.add(ingredient_object)

    def create(self, validated_data):
        """Create a recipe."""
        tags = validated_data.pop("tags", [])
        ingredients = validated_data.pop("ingredients", [])
        recipe = Recipe.objects.create(**validated_data)
        self._get_or_create_tag(tags, recipe)
        self._get_or_create_ingredient(ingredients, recipe)
        return recipe

    def update(self, instance, validated_data):
        """Update a recipe."""
        tags = validated_data.pop("tags", None)
        ingredients = validated_data.pop("ingredients", None)

        if ingredients is not None:
            instance.ingredients.clear()
            self._get_or_create_ingredient(ingredients, instance)

        if tags is not None:
            instance.tags.clear()
            self._get_or_create_tag(tags, instance)

        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)

        instance.save()
        return instance


class RecipeDetailSerializer(RecipeSerializer):
    """Serializer for recipe detail view."""

    class Meta(RecipeSerializer.Meta):
        fields = RecipeSerializer.Meta.fields + ["description"]
