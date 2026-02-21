import base64
import json
import re

from fastapi import APIRouter, File, HTTPException, UploadFile
from openai import AsyncOpenAI

from app.core.config import settings
import app.db.session as supabase_db
from app.schemas.schemas import ItemBase, FavoriteRecipe

router = APIRouter()

# Updated prompt to enforce the exact JSON schema and stringified arrays
PROMPT = (
    "Please break down the ingredients in this image (e.g. 3 tomatoes, 2 cucumbers, "
    "10 avocados, etc...) and generate a recipe that can be made with THESE ingredients. "
    "It doesn't need to use every ingredient, but it should not use additional ingredients. "
    "IMPORTANT: If the image is unclear or you cannot identify specific items, make your absolute best guess based on the context of the image. "
    "DO NOT apologize, DO NOT ask for clarification, and DO NOT output any conversational text. "
    "Please return ONLY the recipe as a JSON array containing a single object with the exact following schema: "
    '[{"Name": "string", "Steps": "stringified array of strings", "Time": integer, "Ingredients": "stringified array of strings"}]. '
    "Example exactly like this: "
    '[{"Name":"15-Minute Pancakes","Steps":"[\\"Whisk dry ingredients\\",\\"Add milk and eggs\\",\\"Cook on buttered skillet\\"]","Time":15,"Ingredients":"[\\"Flour\\",\\"Eggs\\",\\"Milk\\",\\"Butter\\"]"}]'
)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


# ---------- Existing item endpoints ----------

@router.get("/items/")
async def read_items():
    return [{"item_id": 1, "name": "Item 1"}, {"item_id": 2, "name": "Item 2"}]


@router.post("/items/")
async def create_item(item: dict):
    return {"item_id": 3, "name": item["name"]}


@router.post("/recipes/save")
async def save_recipe(recipe: ItemBase):
    supabase_db.save_item_to_db(recipe)


@router.post("/recipes/favorite")
async def favorite_recipe(favorite: FavoriteRecipe):
    return supabase_db.save_favorite_to_db(favorite)

@router.get("/recipes/favorite")
async def get_favorites(user_id: str):
    return supabase_db.get_favorites_from_db(user_id)

# ---------- Image upload → ChatGPT vision ----------

@router.post("/upload-image/")
async def upload_image(file: UploadFile = File(...)):
    """
    Receive an image from the frontend, send it to ChatGPT with a recipe prompt,
    and return the parsed JSON recipe.
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. "
                   f"Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(contents)} bytes). Max is {MAX_FILE_SIZE} bytes.",
        )

    if not settings.openai_api_key and settings.model_url == "https://api.openai.com/v1":
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key is not configured. Set OPENAI_API_KEY in .env",
        )

    image_b64 = base64.b64encode(contents).decode("utf-8")
    data_url = f"data:{file.content_type};base64,{image_b64}"

    client = AsyncOpenAI(
        api_key=settings.openai_api_key or "sk-dummy",
        base_url=settings.model_url,
    )

    try:
        completion = await client.chat.completions.create(
            model=settings.model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            response_format={"type": "text"},
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {exc}")

    if not completion.choices:
        raise HTTPException(status_code=502, detail="ChatGPT returned an empty response (no choices).")

    raw = completion.choices[0].message.content
    if not raw:
        raise HTTPException(status_code=502, detail="ChatGPT returned an empty message content.")

    # Robust JSON extraction
    content = raw.strip()

    # Try to find JSON block in markdown
    if "```" in content:
        # Extract the content between the first and last triple backticks
        match = re.search(r"```(?:json)?\n?(.*?)\n?```", content, re.DOTALL)
        if match:
            content = match.group(1).strip()

    # Try parsing directly
    try:
        recipe_data = json.loads(content)
        return recipe_data
    except json.JSONDecodeError:
        pass  # Continue to fallback

    # Fallback: Try to find the first '[' or '{' and the last ']' or '}' 
    # and parse the content between them.
    for start_char, end_char in [("[", "]"), ("{", "}")]:
        start_idx = content.find(start_char)
        end_idx = content.rfind(end_char)

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                recipe_data = json.loads(content[start_idx : end_idx + 1])
                return recipe_data
            except json.JSONDecodeError:
                continue

    raise HTTPException(status_code=502, detail=f"ChatGPT returned invalid JSON: {raw}")
