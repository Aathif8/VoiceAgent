import os
from dotenv import load_dotenv
from ringcentral import SDK

print("Starting RingCentral JWT auth...")

load_dotenv()

RC_CLIENT_ID = os.getenv("RC_CLIENT_ID")
RC_CLIENT_SECRET = os.getenv("RC_CLIENT_SECRET")
RC_SERVER_URL = os.getenv("RC_SERVER_URL")
RC_JWT = os.getenv("RC_JWT")
RC_REDIRECT_URI = os.getenv("RC_REDIRECT_URI")
sdk = SDK(RC_CLIENT_ID, RC_CLIENT_SECRET, RC_SERVER_URL)

platform = sdk.platform()

def get_auth_url():
    return platform.auth_url()


def login_with_auth_code(code):
    platform.login(code=code, redirect_uri=RC_REDIRECT_URI)
    return platform.auth().data()