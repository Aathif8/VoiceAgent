import openai
import time
import os
import requests
import json
from services.upload_service import get_chroma_collections
from fastapi import APIRouter
from dotenv import load_dotenv
import assemblyai as aai
import tempfile
from datetime import datetime

router = APIRouter()

# Load Environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Initialize AssemblyAI
aai.settings.api_key = os.getenv("ASSEMBLY_API_KEY")

OPEN_ROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
HEADERS = {
    "Authorization": f"Bearer {OPEN_ROUTER_API_KEY}",
    "Content-Type": "application/json"
    }

# Initialize Twilio
Twilio_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
Twilio_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_AUTH = (Twilio_ACCOUNT_SID, Twilio_AUTH_TOKEN)

# Function to get audio file from Twilio
def fetch_recording(url, retries=3, delay=2):
    for attempt in range(retries):
        response = requests.get(url, auth=TWILIO_AUTH)
        if response.status_code == 200:
            return response.content
        else:
            print(f"Attempt {attempt + 1} failed, retrying in {delay} seconds...")
            time.sleep(delay)
    raise Exception(f"Failed to fetch recording after {retries} attempts")


# Function to transcribe audio
def transcribe_audio(audio_bytes: bytes, recording_sid: str = None):
    try:
        if not audio_bytes:
            raise Exception("Downloaded audio is empty")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp:
            temp.write(audio_bytes)
            temp.flush()

        # Check the file size
        print(f"File size: {os.path.getsize(temp.name)} bytes")

        config = aai.TranscriptionConfig(speech_model=aai.SpeechModel.best)
        transcriber = aai.Transcriber(config=config)
        transcript = transcriber.transcribe(temp.name)

        print(f"[{recording_sid}] Transcription succeeded")
        return transcript.text
    
    except aai.types.TranscriptError as e:
        print(f"[{recording_sid}] AssemblyAI error: {e}")
        return "Transcription failed due to processing error."

    except Exception as e:
        print(f"[{recording_sid}] General error: {e}")
        return "Internal error during transcription."
    

# Function to retrieve relevant data from ChromaDB
def retrieve_relevant_data(query):
    if not query or not isinstance(query, str):
        raise ValueError("Query must be a non-empty string.")
    
    query = query.strip()
    if len(query) > 8192:  # max token limit for embeddings
        query = query[:8192]
        
    query_embedding_response = openai.embeddings.create(
        model="text-embedding-ada-002",
        input=[query]
    )
    query_embedding = query_embedding_response.data[0].embedding

    results = get_chroma_collections().query(
        query_embeddings=[query_embedding],
        n_results=3
    )

    relevant_texts = " ".join(results["documents"][0] if results["documents"] else "No relevant data found")
    print("Relevant Data Extracted")
    return relevant_texts

# Function to generate response
def generate_response(conversation:list):
    current_time = datetime.now().strftime("%A, %d %B %Y at %I:%M %p")

    prompt = f"""
    You are a friendly healthcare assistant at ABC Hospital. Help the user book an appointment.

    Today's date is and time is: {current_time}
    
    Only assist with appointment-related queries. If the user says something like "I want to book an appointment", then begin asking the following details in a step-by-step manner:
    1. Full name
    2. Preferred appointment **date (from today onwards only)**
    3. Preferred appointment time (must be future time from now)
    4. Department or doctor
    5. Reason for the appointment
    6. Specific requirements, if any
    7. Contact number
    
    Do **not** make up any information or confirm anything without the user saying it.

    Always respond politely and clearly. Never invent fake doctors, times, or departments.

    Respond in a friendly and professional manner.
    
    Conversation so far:
    {chr(10).join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in conversation])}
    Your response:
    """
    
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=HEADERS,
        data=json.dumps({
            "model": "meta-llama/llama-4-maverick:free",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
        })
    )

    if response.status_code == 200:
        result = response.json()
        print("Response Generated Successfully")
        return result["choices"][0]["message"]["content"] if result else "No response from model."
    else:
        return f"Error: {response.status_code} - {response.text}"