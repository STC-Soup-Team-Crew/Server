from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import router as api_router
from app.api.v1.billing_endpoints import router as billing_router
from app.api.v1.impact_endpoints import router as impact_router

app = FastAPI(
    title="MealMaker API",
    description="API for recipe generation, food sharing, and environmental impact tracking",
    version="1.0.0"
)

# --- CORS: allow the frontend to call this API ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix="/api/v1")
app.include_router(billing_router, prefix="/api/v1")
app.include_router(impact_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to my FastAPI application!"}
