import os
from services.upload_service import extract_from_file, store_data_in_chroma

def load_file(folder_path="data"):
    print("Loading files into ChromaDB...")
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        print(f"Loading {filename} from {folder_path}...")
        if not filename.lower().endswith(('.pdf', '.docx', '.txt')):
            continue

        try:
            with open(file_path, "rb") as f:
                file_bytes = f.read()
                
                text = extract_from_file(file_bytes, filename)
                if text:
                    store_data_in_chroma(text, source=filename)
                    print(f"Successfully loaded {filename} into ChromaDB.")
        except Exception as e:
            print(f"Error processing {filename}: {e}")