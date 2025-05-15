from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse
from utils.ringcentral_auth import get_auth_url, login_with_auth_code
from services.ringcentral_service import handle_ringcentral_event

router = APIRouter()


@router.get("/ringcentral/login")
def ringcentral_login():
    url = get_auth_url()
    return RedirectResponse(url=url)

@router.get("/oauth2callback")
def oauth2callback(code: str):
    try:
        token = login_with_auth_code(code)
        return JSONResponse(content={"message": "OAuth login successful", "token": token})
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    
@router.post("/ringcentral/webhook")
async def ringcentral_webhook(request: Request):
    validation_token = request.headers.get("Validation-Token")
    if validation_token:
        return JSONResponse(content={}, headers={"Validation-Token": validation_token})
    
    data = await request.json()
    await handle_ringcentral_event(data)
    return {"status": "received"}