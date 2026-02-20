from fastapi import APIRouter, FastAPI, File, UploadFile
import shutil

app = FastAPI()

router = APIRouter()

@app.post("/upload-photo/")
async def upload_photo(file: UploadFile = File(...)):
    # You can access metadata like filename and content type
    print(f"Uploading: {file.filename} ({file.content_type})")
    
    # Save the file locally
    with open(f"saved_{file.filename}", "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"filename": file.filename, "type": file.content_type}


@router.get("/items/")
async def read_items():
    return [{"item_id": 1, "name": "Item 1"}, {"item_id": 2, "name": "Item 2"}]

@router.post("/items/")
async def create_item(item: dict):
    return {"item_id": 3, "name": item["name"]}