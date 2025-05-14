import os
import json
from dotenv import load_dotenv
from ringcentral import SDK

print("Starting RingCentral JWT auth...")

load_dotenv()

RC_CLIENT_ID = os.getenv("RC_CLIENT_ID")
RC_CLIENT_SECRET = os.getenv("RC_CLIENT_SECRET")
RC_SERVER_URL = os.getenv("RC_SERVER_URL")
RC_JWT = os.getenv("RC_JWT")
sdk = SDK(RC_CLIENT_ID, RC_CLIENT_SECRET, RC_SERVER_URL)

platform = sdk.platform()

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


# Perform Jwt login
try: 
    platform.login(
        jwt=RC_JWT
    )
    print("Login Successfully!")

    # Get token data
    token = platform.auth().data()

    # Print Token
    print(json.dumps(token, indent=2))

    # Save token to file
    with open(".token.json", "w") as f:
        json.dump(token, f)
    print("Token save to file")

    register_webhook()

except Exception as e:
    print("Login failed", str(e))