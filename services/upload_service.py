import fitz
import io
import openai
import chromadb
from docx import Document
from fastapi import HTTPException


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
    existing_ids = collection.get(include=[])["ids"]

    if source in existing_ids:
        print(f"Skipping {source} as it already exists in the database.")
        return
    
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

    print(f"Stored {source} in ChromaDB.")

def get_chroma_collections():
    return collection