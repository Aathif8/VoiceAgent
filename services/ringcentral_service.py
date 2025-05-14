async def handle_ringcentral_event(data):
    event_type = data.get("event")
    body = data.get("body", {})
    if event_type == "/restapi/v1.0/account/~/telephony/sessions":
        parties = body.get("parties", [])
        if not parties:
            return
        
        party = parties[0]
        session_id = body.get("sessionId")
        party_id = party.get("id")

        # Play initial IVR prompt
        play_audio(session_id, party_id, "https://voiceagent-0wtp.onrender.com/static/ivr_intro.mp3")


def play_audio(session_id, party_id, audio_url):
    from utils.ringcentral_auth import platform
    platform.post(f"//restapi/v1.0/account/~/telephony/sessions/{session_id}/parties/{party_id}/play", {
        "audioFile": {
            "url": audio_url
        }
    })

