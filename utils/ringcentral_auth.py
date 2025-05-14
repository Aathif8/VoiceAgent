import os
from dotenv import load_dotenv
from ringcentral import SDK

load_dotenv()

sdk = SDK(os.getenv("RC_CLIENT_ID"), os.getenv("RC_CLIENT_SECRET"), os.getenv("RC_SERVER_URL"))

platform = sdk.platform()
platform.login(jwt=os.getenv("RC_JWT"))

def register_webhook():
    url = "https://voiceagent-0wtp.onrender.com/ringcentral/webhook"
    event_filters = [
        "/restapi/v1.0/account/~/telephony/sessions"
    ]
    body = {
        "eventFilters": event_filters,
        "deliveryMode": {
            "transportType": "WebHook",
            "address": url
        }
    }
    response = platform.post("/restapi/v1.0/subscription", body)
    print("Webhook Registered", response.json())