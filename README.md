# STC Hackathon – Recipe Vision API

A FastAPI server that accepts an image from the frontend, sends it to **ChatGPT (GPT-4o vision)** with a recipe prompt, and returns a structured JSON recipe.

---

## How it works

```
Frontend  →  POST /api/v1/upload-image/  →  GPT-4o vision  →  JSON recipe  →  Frontend
```

The server:
1. Validates the uploaded image (JPEG, PNG, WebP, or GIF; ≤ 10 MB).
2. Base64-encodes the image and sends it to GPT-4o alongside a fixed prompt that asks the model to identify ingredients and produce a recipe.
3. Returns the parsed JSON recipe directly to the caller.

### Recipe JSON shape

```json
{
  "name": "string",
  "ingredients": ["string", ...],
  "time": 30,
  "steps": ["string", ...]
}
```

---

## Project structure

```
Server/
├── app/
│   ├── main.py                  # FastAPI app + CORS
│   └── api/v1/
│       └── endpoints.py         # POST /upload-image/ + misc item endpoints
│   └── core/
│       └── config.py            # Settings (reads .env)
├── tests/
│   └── test_main.py             # Pytest test suite
├── requirements.txt
├── Dockerfile
└── .env                         # Not committed – see below
```

---

## Setup (local)

### 1. Prerequisites

- Python 3.9+
- An [OpenAI API key](https://platform.openai.com/api-keys) with GPT-4o access

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate        # fish: source .venv/bin/activate.fish
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-...
```

### 5. Run the server

```bash
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`.  
Interactive docs: `http://127.0.0.1:8000/docs`

---

## Running with Docker

```bash
# Build
docker build -t stc-api .

# Run (pass your API key at runtime)
docker run -p 8000:8000 -e OPENAI_API_KEY=sk-... stc-api
```

---

## API reference

### `POST /api/v1/upload-image/`

Upload an image and receive a recipe.

**Request** – `multipart/form-data`

| Field | Type | Description |
|-------|------|-------------|
| `file` | file | Image file (JPEG, PNG, WebP, GIF; max 10 MB) |

**Response 200** – JSON recipe

```json
{
  "name": "Avocado Tomato Salad",
  "ingredients": ["3 tomatoes", "2 avocados", "salt"],
  "time": 10,
  "steps": ["Dice the tomatoes.", "Slice the avocados.", "Season and mix."]
}
```

**Error responses**

| Code | Reason |
|------|--------|
| 400  | Unsupported file type |
| 413  | File exceeds 10 MB |
| 500  | `OPENAI_API_KEY` not set |
| 502  | OpenAI API error or returned invalid JSON |

---

## Testing

```bash
pytest tests/test_main.py -v
```

The test suite covers:
- Root endpoint
- File type rejection (non-image)
- Oversized file rejection
- Missing API key
- Happy path (mocked OpenAI response)
- OpenAI network/API errors
- Invalid JSON returned by OpenAI
- All four accepted MIME types (parametrized)

---

## Billing endpoints (Stripe + Clerk)

- `POST /api/v1/billing/mobile-payment-sheet` (Clerk Bearer token required)
- `POST /api/v1/billing/customer-portal` (Clerk Bearer token required)
- `POST /api/v1/billing/webhook` (Stripe webhook signature required)

### Billing environment variables

```env
STRIPE_SECRET_KEY=sk_live_or_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
CLERK_SECRET_KEY=sk_live_or_test_...
# Optional:
CLERK_JWT_ISSUER=https://your-clerk-domain
CLERK_JWT_AUDIENCE=your-audience
BILLING_RETURN_URL=mealmaker://billing-return
BILLING_MERCHANT_DISPLAY_NAME=MealMaker
```
