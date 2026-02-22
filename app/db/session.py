import os
from supabase import create_client, Client
from dotenv import load_dotenv
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schemas.schemas import ItemBase, FavoriteRecipe, FridgeListingCreate

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
    """Return recipes whose Ingredients list or Name matches at least one of the queried terms (case-insensitive)."""
    try:
        response = supabase.table('recipes').select("*").execute()
        all_recipes = response.data or []

        query_lower = [q.strip().lower() for q in ingredients if q.strip()]
        if not query_lower:
            return []

        results = []
        for recipe in all_recipes:
            recipe_name = (recipe.get("Name") or recipe.get("name") or "").lower()

            recipe_ingredients = recipe.get("Ingredients", [])
            # Ingredients may be stored as a JSON string or a list
            if isinstance(recipe_ingredients, str):
                import json as _json
                try:
                    recipe_ingredients = _json.loads(recipe_ingredients)
                except Exception:
                    recipe_ingredients = []
            ingr_lower = [i.lower() for i in recipe_ingredients]

            name_match = any(q in recipe_name for q in query_lower)
            ingredient_match = any(any(q in ingr for ingr in ingr_lower) for q in query_lower)

            if name_match or ingredient_match:
                results.append(recipe)

        return results
    except Exception as e:
        print(f"Error searching recipes: {e}")
        return []


# ---------- Fridge-share helpers ----------

FRIDGE_TABLE = "fridge_listings"


def create_fridge_listing(listing: FridgeListingCreate) -> dict:
    """Insert a new fridge listing and return the created row."""
    try:
        data = listing.model_dump(exclude_none=True)
        data["status"] = "available"
        response = supabase.table(FRIDGE_TABLE).insert(data).execute()
        return response.data[0] if response.data else {}
    except Exception as e:
        print(f"Error creating fridge listing: {e}")
        raise


def get_fridge_listings(status: str = "available") -> list:
    """Return all listings with the given status, newest first."""
    try:
        response = (
            supabase.table(FRIDGE_TABLE)
            .select("*")
            .eq("status", status)
            .order("created_at", desc=True)
            .execute()
        )
        return response.data or []
    except Exception as e:
        print(f"Error fetching fridge listings: {e}")
        return []


def get_fridge_listing_by_id(listing_id: str) -> dict | None:
    """Return a single listing by its id."""
    try:
        response = (
            supabase.table(FRIDGE_TABLE)
            .select("*")
            .eq("id", listing_id)
            .single()
            .execute()
        )
        return response.data
    except Exception as e:
        print(f"Error fetching fridge listing {listing_id}: {e}")
        return None


def claim_fridge_listing(listing_id: str, claimed_by: str, claimed_by_name: str) -> dict | None:
    """Mark a listing as claimed. Returns updated row or None."""
    try:
        response = (
            supabase.table(FRIDGE_TABLE)
            .update({
                "status": "claimed",
                "claimed_by": claimed_by,
                "claimed_by_name": claimed_by_name,
            })
            .eq("id", listing_id)
            .eq("status", "available")  # only claim if still available
            .execute()
        )
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error claiming fridge listing {listing_id}: {e}")
        raise


def delete_fridge_listing(listing_id: str, user_id: str) -> bool:
    """Soft-delete a listing (set status='deleted') — only by the owner."""
    try:
        response = (
            supabase.table(FRIDGE_TABLE)
            .update({"status": "deleted"})
            .eq("id", listing_id)
            .eq("user_id", user_id)
            .execute()
        )
        return bool(response.data)
    except Exception as e:
        print(f"Error deleting fridge listing {listing_id}: {e}")
        raise


def get_user_fridge_listings(user_id: str) -> list:
    """Return all listings posted by a specific user (any status except deleted)."""
    try:
        response = (
            supabase.table(FRIDGE_TABLE)
            .select("*")
            .eq("user_id", user_id)
            .neq("status", "deleted")
            .order("created_at", desc=True)
            .execute()
        )
        return response.data or []
    except Exception as e:
        print(f"Error fetching user fridge listings: {e}")
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
