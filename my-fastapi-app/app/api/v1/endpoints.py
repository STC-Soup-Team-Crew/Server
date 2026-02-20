from fastapi import APIRouter, File, HTTPException, UploadFile
import httpx

from app.core.config import settings

router = APIRouter()

# ---------- Existing item endpoints ----------

@router.get("/items/")
async def read_items():
    return [{"item_id": 1, "name": "Item 1"}, {"item_id": 2, "name": "Item 2"}]


@router.post("/items/")
async def create_item(item: dict):
    return {"item_id": 3, "name": item["name"]}


# ---------- Image upload → external API proxy ----------

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


@router.post("/upload-image/")
async def upload_image(file: UploadFile = File(...)):
    """
    Receive an image from the frontend, forward it to an external
    image-processing API, and return the JSON response.
    """
    # --- Validate content type ---
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. "
                   f"Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}",
        )

    # --- Read & validate file size ---
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(contents)} bytes). Max is {MAX_FILE_SIZE} bytes.",
        )

    # --- Ensure the external API URL is configured ---
    if not settings.external_api_url:
        raise HTTPException(
            status_code=500,
            detail="External API URL is not configured. Set EXTERNAL_API_URL in .env",
        )

    # --- Forward the image to the external API ---
    headers = {}
    if settings.external_api_key:
        headers["Authorization"] = f"Bearer {settings.external_api_key}"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                settings.external_api_url,
                files={"file": (file.filename, contents, file.content_type)},
                headers=headers,
            )
            response.raise_for_status()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="External API request timed out.")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"External API error: {exc.response.text}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach external API: {exc}",
        )

    return response.json()