from fastapi import APIRouter, Form, Request
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse
from services.speech_service import transcribe_audio, generate_response, fetch_recording
from services.data_loader import add_appointment, normalize_date, normalize_time
from typing import Dict, List
import html

router = APIRouter()

# Temporary in-memory storage for conversation history
conversation_memory: Dict[str, List[Dict[str, str]]] = {}


@router.post("/twilio/webhook")
async def twilio_answer(request: Request):
    followup = request.query_params.get("followup") == "true"

    response = VoiceResponse()

    if not followup:
        response.say("Hello! Welcome to Healthcare Hospital You’re speaking with our appointment assistant How can I help you today?")

    response.record(
        action="https://voiceagent-0wtp.onrender.com/api/twilio/handle-recording",
        method="POST",
        max_length=15,
        play_beep=False,
        timeout=3,
        trim="trim-silence"
    )
    response.say("No input received. GoodBye.")
    response.hangup()

    print("Returning TwiML for initial webhook:")
    print(str(response))

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
    
    try:
        # Fetch the audio file from the URL
        audio_data = fetch_recording(RecordingUrl)

        transcribed_text = transcribe_audio(audio_data, recording_sid=RecordingSid)

        if not transcribed_text or "error" in transcribed_text.lower():
            response.say("Sorry, I couldn't understand what you trying to say. Please try again.")
            response.redirect("https://voiceagent-0wtp.onrender.com/api/twilio/webhook?followup=true")
            return Response(content=str(response), media_type="application/xml")

        # update conversation memory
        conversation_memory[CallSid].append({"role": "user", "content": transcribed_text})

        # Generate Assistant response using OpenAI
        assistant_response, extracted_info = generate_response(conversation_memory[CallSid])
        print("Extracted Info:", extracted_info)

        conversation_memory[CallSid].append({"role": "assistant", "content": assistant_response})

        # Ensure response is a safe XML string
        if not isinstance(assistant_response, str):
            assistant_response = str(assistant_response)
        response.say(assistant_response)

        # Prompt user to respond again
        response.record(
            action="https://voiceagent-0wtp.onrender.com/api/twilio/handle-recording?followup=true",
            method="POST",
            max_length=15,
            play_beep=False,
            timeout=3,
            trim="trim-silence"
        )
        response.say("No input received. Goodbye.")
        response.hangup()

        # Normalize user inputs
        normalized_date = normalize_date(extracted_info.get("date"))
        normalized_time = normalize_time(extracted_info.get("time"))

        if extracted_info["name"] and normalized_date and normalized_time:
            status = add_appointment({
                "NAME": extracted_info["name"],
                "DATE": normalized_date,
                "TIME": normalized_time,
                "DEPARTMENT": extracted_info.get("department") or "",
                "REASON": extracted_info.get("reason") or "",
                "REQUIREMENTS": extracted_info.get("requirements") or "",
                "CONTACT": extracted_info.get("contact_number") or ""
            })

            if status == "success":
                response.say("Your appointment has been successfully booked.")
                response.say("Thank you and goodbye.")
                conversation_memory.pop(CallSid, None)
                response.hangup()
                print("Appointment booked and call ended.")
                return Response(content=str(response), media_type="application/xml")
            elif status == "duplicate":
                response.say("You already have an appointment at this date and time. Please try a different slot.")

            elif status == "slot_taken":
                response.say("That appointment slot is already taken. Please choose another time.")

            # Add this check right after the booking block
            end_phrases = ["thank you", "that's all", "no thanks", "bye", "i'm done", "nothing else"]
            if any(phrase in transcribed_text.lower() for phrase in end_phrases):
                response.say("You're welcome. Have a great day!")
                response.hangup()
                print("User said goodbye, call ended.")
                return Response(content=str(response), media_type="application/xml")
    
    except Exception as e:
        print(f"Unhandled error: {e}")
        response.say("Sorry, Something went wrong. Please try again later.")

    # Always return a valid TwiML response
    print("Twilio response:", str(response))
    return Response(content=str(response), media_type="application/xml")