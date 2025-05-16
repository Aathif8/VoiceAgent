import io
from fastapi import APIRouter, Form
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse
import requests
from services.speech_service import transcribe_audio, retrieve_relevant_data, generate_response

router = APIRouter()

@router.post("/twilio/webhook")
async def twilio_answer():
    response = VoiceResponse()
    response.say("Hello! You can ask about the Banking Information after the beep")
    response.record(
        action="https://voiceagent-0wtp.onrender.com/api/twilio/handle-recording",
        method="POST",
        max_length=10,
        play_beep=True,
        timeout=1
    )
    response.say("No input received. GoodBye.")
    response.hangup()
    return Response(content=str(response), media_type="application/xml")

@router.post("/twilio/handle-recording")
async def twilio_webhook(RecordingUrl: str = Form(...), RecordingDuration: str = Form(...)):
    print("Recording handler hit")

    if int(RecordingDuration) == 0:
        response = VoiceResponse()
        response.say("Sorry. I didn't hear anything. Please try again")
        response.redirect("https://voiceagent-0wtp.onrender.comapi/api/twilio/webhook")
        return Response(content=str(response), media_type="application/xml")
    
    # Download the recorded audio from Twilio
    audio_response = requests.get(f"{RecordingUrl}.wav")
    audio_bytes = audio_response.content

    transcribed_text = transcribe_audio(audio_bytes)
    context = retrieve_relevant_data(transcribed_text)
    prompt = f"Use the following context to answer the question:\n\nContext:\n{context}\n\nQuestion:\n{transcribed_text}\n\n"
    answer_text = generate_response(prompt)

    # response_audio_path = generate_speech(answer_text)

    # Response via Twilio
    response = VoiceResponse()
    response.say(answer_text)
    response.redirect("https://voiceagent-0wtp.onrender.com/api/twilio/webhook")
    return Response(content=str(response), media_type="application/xml")