from fastapi import APIRouter, Request, Form
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse
import requests
from services.speech_service import transcribe_audio, retrieve_relevant_data, generate_response, generate_speech

router = APIRouter()

@router.post("/twilio/webhook")
async def twilio_webhook(request: Request, RecordingUrl: str = Form(...), RecordingDuration: int = Form(...)):
    if RecordingDuration == 0:
        return Response(status_code=200)
    
    # Download the recorded audio from Twilio
    recording_url = f"{RecordingUrl}.wav"
    audio_response = requests.get(recording_url)
    audio_bytes = audio_response.content

    transcribed_text = transcribe_audio(audio_bytes)
    
    context = retrieve_relevant_data(transcribed_text)
    
    prompt = f"Use the following context to answer the question:\n\nContext:\n{context}\n\nQuestion:\n{transcribed_text}\n\n"

    answer_text = generate_response(prompt)

    response_audio_path = generate_speech(answer_text)

    # Send TwiML response pointing to audio URL
    response = VoiceResponse()
    response.say(answer_text)

    return Response(content=str(response), media_type="application/xml")