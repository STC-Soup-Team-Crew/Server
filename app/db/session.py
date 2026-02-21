import os
from supabase import create_client, Client
from dotenv import load_dotenv
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schemas.schemas import ItemBase

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


if __name__ == "__main__":
    new_recipe = ItemBase(
        Name="15-Minute Pancakes",
        Steps=["Whisk dry ingredients", "Add milk and eggs",
               "Cook on buttered skillet"],
        Ingredients=["Flour", "Eggs", "Milk", "Butter"],
        Time=15
    )

    save_item_to_db(new_recipe)
