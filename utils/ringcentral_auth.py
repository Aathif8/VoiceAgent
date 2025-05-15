import os
import urllib.parse
from dotenv import load_dotenv
from ringcentral import SDK

load_dotenv()

RC_CLIENT_ID = os.getenv("RC_CLIENT_ID")
RC_CLIENT_SECRET = os.getenv("RC_CLIENT_SECRET")
RC_SERVER_URL = os.getenv("RC_SERVER_URL")
RC_REDIRECT_URI = os.getenv("RC_REDIRECT_URI")

print("Starting RingCentral JWT auth...")

sdk = SDK(RC_CLIENT_ID, RC_CLIENT_SECRET, RC_SERVER_URL)
platform = sdk.platform()

def get_auth_url(state=""):
    base_url = f"{RC_SERVER_URL}/restapi/oauth/authorize"
    params = {
        "response_type": "code",
        "client_id": RC_CLIENT_ID,
        "redirect_uri": RC_REDIRECT_URI,
        "state": state
    }
    return f"{base_url}?{urllib.parse.urlencode(params)}"


def login_with_auth_code(code):
    print("Logging in with code:", code)
    
    platform.login(code=code, redirect_uri=RC_REDIRECT_URI)

    # Register Webhook after login
    webhook_response = platform.post('/restapi/v1.0/subscription', {
        "eventFilters": [
            "/restapi/v1.0/account/~/telephony/sessions"
        ],
        "delivery_mode": {
            "transportType": "WebHook",
            "address": "https://voiceagent-0wtp.onrender.com/ringcentral/webhook"
        },
        "expiresIn": 3600
    })

    print("Webhook created:", webhook_response.json_dict())
    return platform.auth().data()