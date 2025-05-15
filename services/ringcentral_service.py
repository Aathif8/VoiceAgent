from utils.ringcentral_auth import platform

def transfer_call(session_id, party_id, extension):
    platform.post(
        f"/restapi/v1.0/account/~/telephony/sessions/{session_id}/parties/{party_id}/transfer",{
            "extension": {
                "extensionNumber": extension
            }
        }
    )

def play_audio(session_id, party_id, audio_url):
    platform.post(f"/restapi/v1.0/account/~/telephony/sessions/{session_id}/parties/{party_id}/play", {
        "audioFile": {
            "url": audio_url
        }
    })

def detect_dtmf(session_id, party_id):
    platform.post(f"/restapi/v1.0/account/~/telephony/sessions/{session_id}/parties/{party_id}/input", {
        "dtmf": {
            "type": "Detect"
        }
    })
async def handle_ringcentral_event(data):
    body = data.get("body", {})
    session_id = body.get("sessionId")
    parties = body.get("parties", [])

    if not parties:
        return
    
    party = parties[0]
    party_id = party.get("id")
    status_code = party.get("status", {}).get("code")

    # Handle Connected status - play IVR and listen for DTMF
    if status_code == "Answered":
        play_audio(session_id, party_id,"https://voiceagent-0wtp.onrender.com/static/ivr_intro.mp3")
        detect_dtmf(session_id, party_id)

    # Handle DTMF input
    if "dtmf" in body:
        digit = body["dtmf"].get("digit")

        if digit == "1":
            transfer_call(session_id, party_id, 103)
        elif digit == "2":
            play_audio(session_id, party_id, "https://voiceagent-0wtp.onrender.com/static/ivr_intro.mp3")