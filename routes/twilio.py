from fastapi import APIRouter, Form, Request
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse
from services.speech_service import transcribe_audio, generate_response, fetch_recording
from services.data_loader import add_appointment, normalize_date, normalize_time
from typing import Dict, List

router = APIRouter()

# Temporary in-memory storage for conversation history
conversation_memory: Dict[str, List[Dict[str, str]]] = {}


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
        timeout=4
    )
    response.say("No input received. GoodBye.")
    response.hangup()
    return Response(content=str(response), media_type="application/xml")

@router.post("/twilio/handle-recording")
async def twilio_webhook(RecordingUrl: str = Form(...), RecordingDuration: str = Form(...), RecordingSid: str = Form(...), From: str = Form(...), CallSid: str = Form(...)):
    print("Recording handler hit")
    print(f"Recording URL: {RecordingUrl}")

    print(f"Caller: {From}")
    if CallSid not in conversation_memory:
        conversation_memory[CallSid] = []

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

    # Add to memory
    conversation_memory[CallSid].append({"role": "user", "content": transcribed_text})

    # Generate Assistant response using OpenAI
    assistant_response, extracted_info = generate_response(conversation_memory[CallSid])
    print("Extracted Info:", extracted_info)

    conversation_memory[CallSid].append({"role": "assistant", "content": assistant_response})

    # Response via Twilio
    response.say(assistant_response)

    # Normalize user inputs
    normalized_date = normalize_date(extracted_info.get("date"))
    normalized_time = normalize_time(extracted_info.get("time"))

    if extracted_info["name"] and normalized_date and normalized_time:
        success = add_appointment({
            "NAME": extracted_info["name"],
            "DATE": normalized_date,
            "TIME": normalized_time,
            "DEPARTMENT": extracted_info.get("department") or "",
            "REASON": extracted_info.get("reason") or "",
            "REQUIREMENTS": extracted_info.get("requirements") or "",
            "CONTACT": extracted_info.get("contact_number") or ""
        })

        if success:
            response.say("Your appointment has been successfully booked.")
            response.say("Thank you and goodbye.")
            conversation_memory.pop(CallSid, None)
            response.hangup()
            return Response(content=str(response), media_type="application/xml")
        else:
            response.say("That slot is already taken or a duplicate entry was found. Please choose another date or time.")