from utils.ringcentral_auth import platform

def transfer_call(session_id, party_id, target_number):
    platform.post(
        f"/restapi/v1.0/account/~/telephony/sessions/{session_id}/parties/{party_id}/transfer",
        {
            "phoneNumber": target_number
        }
    )

def play_audio(session_id, party_id, audio_url):
    platform.post(f"//restapi/v1.0/account/~/telephony/sessions/{session_id}/parties/{party_id}/play", {
        "audioFile": {
            "url": audio_url
        }
    })

async def handle_ringcentral_event(data):
    event_type = data.get("event")
    body = data.get("body", {})
    parties = body.get("parties", [])
    print(f"Received event type: {event_type}")

    if event_type != "/restapi/v1.0/account/~/telephony/sessions":
        return

    if not parties:
        return
    
    party = parties[0]
    session_id = body.get("sessionId")
    party_id = party.get("id")

    # Handle Connected status - play IVR and listen for DTMF
    if party.get("status", {}).get("code") == "Connected":
        play_audio(session_id, party_id,"https://voiceagent-0wtp.onrender.com/static/ivr_intro.mp3")

        platform.post(f"/restapi/v1.0/account/~/telephony/sessions/{session_id}/parties/{party_id}/input", {
            "dtmf": {
                "type": "Detect"
            }
        })

    # Handle DTMF input
    if "dtmf" in body:
        digit = body["dtmf"].get("digit")

        if digit == "1":
            transfer_call(session_id, party_id, +12145566491)
        elif digit == "2":
            play_audio(session_id, party_id, "https://voiceagent-0wtp.onrender.com/static/ivr_intro.mp3")