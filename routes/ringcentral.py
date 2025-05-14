from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from services.ringcentral_service import handle_ringcentral_event

router = APIRouter()

@router.post("/ringcentral/webhook")
async def ringcentral_webhook(request: Request):
    validation_token = request.headers.get("Validation-Token")
    if validation_token:
        return JSONResponse(content={}, headers={"Validation-Token": validation_token})
    
    data = await request.json()
    await handle_ringcentral_event(data)
    return {"status": "received"}