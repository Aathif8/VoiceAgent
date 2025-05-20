import openai
import time
import os
import requests
import json
import re
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


# Function to generate speech from text
def generate_speech(text):
    response = openai.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text
    )
    print("Converted to Audio from response")

    # Save to temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    temp_file.write(response.content)
    temp_file.close()
    
    return temp_file.name


# Function to generate response
def generate_response(conversation:list):
    current_time = datetime.now().strftime("%A, %d %B %Y at %I:%M %p")

    # Extract the user message
    extracted_user_info = {
        "name": None,
        "date": None,
        "time": None,
        "department": None,
        "reason": None,
        "requirements": None,
        "contact_number": None
    }

    for message in conversation:
        if message["role"] == "user":
            content = message["content"].lower()
            # Extracting user name
            if not extracted_user_info["name"] and "my name is" in content:
                extracted_user_info["name"] = content.split("my name is")[-1].strip()[0]
            # Extracting appointment date
            if not extracted_user_info["date"] and any(month in content for month in ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december", "today", "tomorrow"]):
                extracted_user_info["date"] = content
            
            # Extracting appointment time
            if not extracted_user_info['time']:
                time_match = re.search(r'\b\d{1,2}:\d{2}\s*[ap]m\b', content)
                if time_match:
                    extracted_user_info['time'] = time_match.group()
            
            # Extracting department
            if not extracted_user_info["department"] and any(keyword in content for keyword in ["department", "doctor", "dr."]):
                extracted_user_info['department'] = content
            
            # Extracting reason for appointment
            if not extracted_user_info["reason"] and "because" in content:
                extracted_user_info["reason"] = content.split("because")[-1].strip()

            # Extracting specific requirements
            if not extracted_user_info["requirements"] and "i need" in content:
                extracted_user_info["requirements"] = content.split("i need")[-1].strip()

            # Extracting contact number
            if not extracted_user_info['contact_number']:
                contact_match = re.search(r'\b\d{10}\b', content)
                if contact_match:
                    extracted_user_info['contact_number'] = contact_match.group()
    print(f"Extracted User Info: {extracted_user_info}")
    
    prompt = f"""
    You are a friendly healthcare assistant at ABC Hospital. The user has already been greeted, so do not introduce yourself again. Just continue the conversation professionally and help them book an appointment.

    Today's date is and time is: {current_time}
    
    Only assist with appointment-related queries. If the user says something like "I want to book an appointment", then begin asking the following details in a step-by-step manner:
    1. Full name: {extracted_user_info['name'] or 'Not yet Provided'}
    2. Preferred appointment **date (from today onwards only)**: {extracted_user_info['date'] or 'Not yet Provided'}
    3. Preferred appointment time (must be future time from now): {extracted_user_info['time'] or 'Not yet Provided'}
    4. Department or doctor: {extracted_user_info['department'] or 'Not yet Provided'}
    5. Reason for the appointment: {extracted_user_info['reason'] or 'Not yet Provided'}
    6. Specific requirements, if any: {extracted_user_info['requirements'] or 'Not yet Provided'}
    7. Contact number: {extracted_user_info['contact_number'] or 'Not yet Provided'}
    Continue the conversation from the last user message. Ask for the next missing detail **only**, without repeating previous questions.
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