import os
import json
import base64
import asyncio
import websockets
from datetime import datetime
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.websockets import WebSocketDisconnect
from twilio.twiml.voice_response import VoiceResponse, Connect, Say, Stream
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = os.getenv("PORT", 8000)
BASE_URL = "voiceagent-0wtp.onrender.com"

current_time = datetime.now().strftime("%A, %d %B %Y at %I:%M %p")

SYSTEM_MESSAGE = f"""
    You are a friendly appointment assistant at Healthcare Hospital. The user has already been greeted, so do not introduce yourself again. Just continue the conversation professionally and help them book an appointment.

    Today's date is and time is: {current_time}
    
    Only assist with appointment-related queries. If the user says something like "I want to book an appointment", then begin asking the following details in a step-by-step manner:
    1. Full name
    2. Preferred appointment **date (from today onwards only)
    3. Preferred appointment time (must be future time from now)
    4. Department or doctor
    5. Reason for the appointment
    6. Specific requirements, if any
    7. Contact number
    Continue the conversation from the last user message. Ask for the next missing detail **only**, without repeating previous questions.
    Do **not** make up any information or confirm anything without the user saying it.

    Always respond politely and clearly. Never invent fake doctors, times, or departments.

    Respond in a friendly and professional manner.
    """

VOICE = 'alloy'

LOG_EVENT_TYPES = [
    'response.content.done', 'rate_limitts.updated', 'response.done', 'input_audio_buffer.committed', 'input_audio_buffer.speech_stopped', 'input_audio_buffer.speech_started', 'session.created'
]

app = FastAPI()

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in the environment variables.")

@app.get("/", response_class=JSONResponse)
async def index_page():
    return {"message": "Twilio Media stream Service is running."}

@app.api_route("/incoming-call", methods=["GET" ,"POST"])
async def handle_incoming_call(request: Request):
    response = VoiceResponse()
    response.say("Welcome to Healthcare Hospital. Please hold while we connect you to our appointment assistant.")
    response.pause(length=1)
    response.say("Connecting you now.")
    connect = Connect()
    connect.stream(url=f"wss://{BASE_URL}/media-stream")
    response.append(connect)
    return HTMLResponse(content=str(response), media_type="text/xml")

@app.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    print("Client connected")
    await websocket.accept()

    async with websockets.connect(
       'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01',
       extra_headers={
           "Authorization": f"Bearer {OPENAI_API_KEY}",
           "OpenAI-Beta": "relatime=v1"
       } 
    ) as openai_ws:
        await send_session_update(openai_ws)
        stream_sid = None

        async def receive_from_twilio():
            nonlocal stream_sid
            try:
                async for message in websocket.iter_text():
                    data = json.loads(message)
                    if data["event"] == "start":
                        stream_sid = data['start']['stream_sid']
                        print(f"Incoming Stream SID: {stream_sid}")
                    elif data["event"] == "media" and openai_ws.open:
                        audio_append = {
                            "type": "input_audio_buffer.append",
                            "audio": data["media"]["payload"],
                        }
                        await openai_ws.send(json.dumps(audio_append))
            except WebSocketDisconnect:
                print("Client disconnected")
                if openai_ws.open:
                    await openai_ws.close()

        async def send_to_twilio():
            nonlocal stream_sid
            try:
                async for openai_message in openai_ws:
                    response = json.loads(openai_message)
                    if response['type'] in LOG_EVENT_TYPES:
                        print(f"Received event: {response['type']}", response)
                    if response['type'] == 'session.updated':
                        print(f"Session updated successfully:",response)
                    if response['type'] == 'response.audio.delta' and response.get('delta'):
                        try:
                            audio_payload = base64.b64encode(base64.b64decode(response['delta'])).decode('utf-8')
                            audio_delta = {
                                "event": "media",
                                "streamSid": stream_sid,
                                "media": {
                                    "payload": audio_payload,
                                }
                            }
                            await websocket.send_json(audio_delta)
                        except Exception as e:
                            print(f"Error processing audio delta: {e}")
            except Exception as e:
                print(f"Error in send_to_twilio: {e}")
        await asyncio.gather(
            receive_from_twilio(),
            send_to_twilio()
        )

async def send_session_update(openai_ws):
    session_update = {
        "type": "session.update",
        "session": {
            "turn_detection": {"type": "server_vad"},
            "input_audio_input": "g711_ulaw",
            "output_audio_output": "g711_ulaw",
            "voice": VOICE,
            "instruction": SYSTEM_MESSAGE,
            "modalities": ["text", "audio"],
            "temperature": 0.7,
        }
    }
    print('Sending session update:', json.dumps(session_update))
    await openai_ws.send(json.dumps(session_update))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)