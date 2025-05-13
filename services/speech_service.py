import openai
import io
import os
import requests
import json
from services.upload_service import get_chroma_collections
from fastapi import APIRouter
from dotenv import load_dotenv
import assemblyai as aai
import tempfile

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

# Functioon to transcribe audio
def transcribe_audio(audio_bytes):
    audio_file = io.BytesIO(audio_bytes)

    config = aai.TranscriptionConfig(speech_model=aai.SpeechModel.best)

    response = aai.Transcriber(config=config).transcribe(audio_file)

    return response.text

# Function to retrieve relevant data from ChromaDB
def retrieve_relevant_data(query):
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
def generate_response(prompt:str):
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