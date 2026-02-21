import os
from supabase import create_client, Client
from dotenv import load_dotenv
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schemas.schemas import ItemBase, FavoriteRecipe

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# Insert it into the database
def save_item_to_db(item: ItemBase):
    try:
        data_to_insert = item.model_dump(exclude_none=True)
        response = supabase.table('recipes').insert(data_to_insert).execute()
        print("Successfully saved:", response.data)
        return response.data

    except Exception as e:
        print(f"Error saving to Supabase: {e}")


def save_favorite_to_db(favorite: FavoriteRecipe):
    try:
        data_to_insert = favorite.model_dump(exclude_none=True)
        # We assume a 'favorites' table exists or will be created
        response = supabase.table('favorites').insert(data_to_insert).execute()
        print("Successfully saved favorite:", response.data)
        return response.data

    except Exception as e:
        print(f"Error saving favorite to Supabase: {e}")


def get_favorites_from_db(user_id: str):
    try:
        response = supabase.table('favorites').select("*").eq("user_id", user_id).execute()
        print("Successfully fetched favorites:", response.data)
        return response.data
    except Exception as e:
        print(f"Error fetching favorites: {e}")
        return []


def search_recipes_by_ingredients(ingredients: list):
    """Return recipes whose Ingredients list contains at least one of the queried ingredients (case-insensitive)."""
    try:
        response = supabase.table('recipes').select("*").execute()
        all_recipes = response.data or []

        query_lower = [q.strip().lower() for q in ingredients if q.strip()]
        if not query_lower:
            return []

        results = []
        for recipe in all_recipes:
            recipe_ingredients = recipe.get("Ingredients", [])
            # Ingredients may be stored as a JSON string or a list
            if isinstance(recipe_ingredients, str):
                import json as _json
                try:
                    recipe_ingredients = _json.loads(recipe_ingredients)
                except Exception:
                    recipe_ingredients = []
            ingr_lower = [i.lower() for i in recipe_ingredients]
            if any(any(q in ingr for ingr in ingr_lower) for q in query_lower):
                results.append(recipe)

        return results
    except Exception as e:
        print(f"Error searching recipes: {e}")
        return []


if __name__ == "__main__":
    new_recipe = ItemBase(
        Name="15-Minute Pancakes",
        Steps=["Whisk dry ingredients", "Add milk and eggs",
               "Cook on buttered skillet"],
        Ingredients=["Flour", "Eggs", "Milk", "Butter"],
        Time=15
    )

    save_item_to_db(new_recipe)
