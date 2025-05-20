from fastapi import APIRouter, Form, Request
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse
from services.speech_service import transcribe_audio, retrieve_relevant_data, generate_response, fetch_recording

router = APIRouter()

conversation_memory = {}

@router.post("/twilio/webhook")
async def twilio_answer(request: Request):
    followup = request.query_params.get("followup") == "true"

    response = VoiceResponse()

    if not followup:
        response.say("Hello! I am an Clinic Assistant at ABC Hospital. Please ask your queries after the beep")

    response.record(
        action="https://voiceagent-0wtp.onrender.com/api/twilio/handle-recording",
        method="POST",
        max_length=30,
        play_beep=True,
        timeout=1
    )
    response.say("No input received. GoodBye.")
    response.hangup()
    return Response(content=str(response), media_type="application/xml")

@router.post("/twilio/handle-recording")
async def twilio_webhook(RecordingUrl: str = Form(...), RecordingDuration: str = Form(...), RecordingSid: str = Form(...)):
    print("Recording handler hit")
    print(f"Recording URL: {RecordingUrl}")

    try:
        duration = int(RecordingDuration)
    except (ValueError, TypeError):
        duration = 0

    response = VoiceResponse()

    if duration == 0:
        response.say("Sorry. I didn't hear anything. Please try again")
        response.redirect("https://voiceagent-0wtp.onrender.com/api/twilio/webhook")
        return Response(content=str(response), media_type="application/xml")
    
    # Fetch the audio file from the URL
    recording_url = fetch_recording(RecordingUrl)

    transcribed_text = transcribe_audio(recording_url, recording_sid=RecordingSid)

    if not transcribed_text or "error" in transcribed_text.lower():
        transcribed_text = "Sorry, I couldn't understand what you trying to say. Please try again."
        response.redirect("https://voiceagent-0wtp.onrender.com/api/twilio/webhook?followup=true")
        return Response(content=str(response), media_type="application/xml")

    # Get or initialize conversation memory
    conversation = conversation_memory.get(RecordingSid, [])
    conversation.append({"role": "user", "content": transcribed_text})
    print(f"Transcribed text: {transcribed_text}")

    assistant_response = generate_response(conversation)

    conversation.append({"role": "assistant", "content": assistant_response})

    conversation_memory[RecordingSid] = conversation

    # Response via Twilio
    response.say(assistant_response)

    if "confirmed" in assistant_response.lower() or "your appointment is confirmed" in assistant_response.lower():
        response.say("Thank you for confirming. Goodbye.")
        response.hangup()
    else:
        response.redirect("https://voiceagent-0wtp.onrender.com/api/twilio/webhook?followup=true")
    return Response(content=str(response), media_type="application/xml")