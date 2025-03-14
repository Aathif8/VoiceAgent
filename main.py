#Importing Necessary Dependencies
import os
import openai
import chromadb
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import io
import fitz
from docx import Document
from fastapi.middleware.cors import CORSMiddleware

# Load Environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Initializing FastAPI
app = FastAPI()

# Allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize ChromaDB client
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="knowledge_base")

# Function to extract text from a file
def extract_from_file(file_bytes, filename):
    ext = filename.split(".")[-1].lower()
    text = ""

    if ext == "pdf":
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page in doc:
            text += page.get_text("text") + "\n"
    elif ext == "docx":
        doc = Document(io.BytesIO(file_bytes))
        for para in doc.paragraphs:
            text += para.text + "\n"
    elif ext == "txt":
        text = file_bytes.decode("utf-8")
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format. Use PDF, Docx, or Txt")
    
    return text.strip()

# Function to stroe extracted text in chromaDB
def store_data_in_chroma(text, source):
    response = openai.embeddings.create(
        model="text-embedding-ada-002",
        input=[text]
    )
    embedding = response.data[0].embedding

    # Store in ChromaDB
    collection.add(
        documents=[text],
        embeddings=[embedding],
        ids=[source]
    )

# API to upload and store files in ChromaDB
@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    file_bytes = await file.read()

    try:
        extracted_text = extract_from_file(file_bytes, file.filename)
        store_data_in_chroma(extracted_text, file.filename)
        return {"message": f"File '{file.filename}' processed and stored successfully!"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# Functioon to transcribe audio
def transcribe_audio(audio_bytes):
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "audio.mp3"

    response = openai.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file
    )

    return response.text

# Function to retrieve relevant data from ChromaDB
def retrieve_relevant_data(query):
    query_embedding_response = openai.embeddings.create(
        model="text-embedding-ada-002",
        input=[query]
    )
    query_embedding = query_embedding_response.data[0].embedding

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )

    relevant_texts = " ".join(results["documents"][0] if results["documents"] else "No relevant data found")
    return relevant_texts

# Function to generate response
def generate_response(query, context):
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user", 
                "content": f"Context: {context}\n\nQuery: {query}"
            }
        ]
    )
    
    return response.choices[0].message.content

# Function to generate speech from text
def generate_speech(text):
    response = openai.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text
    )

    temp_audio_path = "output_audio.mp3"
    with open(temp_audio_path, "wb") as audio_file:
        audio_file.write(response.content)

    return temp_audio_path

# API to process audio, and retrieve response in audio
@app.post("/process_audio/")
async def process_audio(file: UploadFile = File(...)):
    audio_bytes = await file.read()

    # Transcribe Audio
    transcribed_text = transcribe_audio(audio_bytes)

    # Retrieve Context from ChromaDB
    relevant_text = retrieve_relevant_data(transcribed_text)

    # Generate Response using OpenAI
    response_text = generate_response(transcribed_text, relevant_text)

    # Response Audio from Text
    output_audio = generate_speech(response_text)

    # Saving the transcription and response text in temp file
    text_file_path = "response.txt"
    with open(text_file_path, "w", encoding="utf-8") as text_file:
        text_file.write(f"Transcription:\n{transcribed_text}\n\nResponse:\n{response_text}")

    # Return the audio file
    return {
        "transcription": transcribed_text,
        "response": response_text,
        "audioFile": FileResponse(output_audio, media_type="audio/mpeg", filename="response.mp3")
        }

