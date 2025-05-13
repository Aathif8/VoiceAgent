from fastapi import APIRouter, UploadFile, File, HTTPException
from services.upload_service import extract_from_file, store_data_in_chroma

router = APIRouter()

@router.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    file_bytes = await file.read()

    try:
        extracted_text = extract_from_file(file_bytes, file.filename)
        store_data_in_chroma(extracted_text, file.filename)
        return {"message": f"File '{file.filename}' processed and stored successfully!"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))