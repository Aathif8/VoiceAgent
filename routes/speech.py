from fastapi import APIRouter
from fastapi import UploadFile, File
from fastapi.responses import FileResponse
from services.speech_service import transcribe_audio, retrieve_relevant_data, generate_response, generate_speech

router = APIRouter()

# API to process audio, and retrieve response in audio
@router.post("/process_audio/")
async def process_audio(file: UploadFile = File(...)):
    audio_bytes = await file.read()

    # Transcribe Audio
    transcribed_text = transcribe_audio(audio_bytes)

    # Retrieve Context from ChromaDB
    relevant_text = retrieve_relevant_data(transcribed_text)

    # Generate Response using OpenRouter
    input_text = transcribed_text.lower()
    prompt = (
        f"Use the following context to answer the question:\n\n"
        f"Context:\n{relevant_text}\n\n"
        f"Question:\n{input_text}\n\n"
    )
    response_text = generate_response(prompt)

    # Response Audio from Text
    audio_stream = generate_speech(response_text)

    return FileResponse(
        audio_stream,
        media_type="audio/wav",
        filename="response.wav"
    )