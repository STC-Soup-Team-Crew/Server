from fastapi import FastAPI
from app.api.v1.endpoints import router as api_router

app = FastAPI()

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to my FastAPI application!"}