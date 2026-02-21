import base64
import json
import re

from fastapi import APIRouter, File, HTTPException, UploadFile
from openai import AsyncOpenAI

from app.core.config import settings

router = APIRouter()

PROMPT = (
    "Please break down the ingredients in this image (e.g. 3 tomatoes, 2 cucumbers, "
    "10 avacados, etc...) and generate a recipe that can be made with THESE ingredients. "
    "It doesn't need to use every ingredient, but it should not use additional ingredients. "
    "please return ONLY the recipe as a .json file with the name as a string, ingredients "
    "as an array of strings, integer time in minutes, and steps as an array of string"
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
    
    # If it still doesn't parse, try to find the first '{' and last '}'
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Fallback: Find the first { and last }
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(content[start:end+1])
            except json.JSONDecodeError:
                pass
        
        raise HTTPException(status_code=502, detail=f"ChatGPT returned invalid JSON: {raw}")
