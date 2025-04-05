import os
import io
import json
import asyncio
from datetime import datetime
from typing import List, Dict
import uuid
import numpy as np
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
import PyPDF2
from docx import Document  # For handling .docx files

from fastapi import UploadFile, File, FastAPI
from fastapi.middleware.cors import CORSMiddleware


try:
    import google.generativeai as genai
except ImportError:
    raise ImportError("The 'google-generativeai' module is not installed. Please install it using 'pip install google-generativeai'.")

load_dotenv()


# ===== Configuration =====
DATA = os.path.join("data")
os.makedirs(DATA, exist_ok=True)


while True:
    unique_filename = f"embeddings_{uuid.uuid4().hex}.json"
    STORAGE_PATH = os.path.join(DATA, unique_filename)
    if not os.path.exists(STORAGE_PATH):
        break

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ===== Gemini Client =====
class GeminiClient:
    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    async def generate_content(self, prompt: str) -> str:
        try:
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            return f"[Error generating response: {str(e)}]"

# ===== Dummy Embedding Function =====
def get_dummy_embedding(text):
    return np.round(np.random.rand(128), 3)

gemini_client = GeminiClient()

# ===== Universal File Loader =====
def load_user_file(file_data, filename: str) -> List[Dict]:
    try:
        filename = filename.lower()

        if filename.endswith(".txt"):
            content = file_data.read().decode("utf-8")
        elif filename.endswith(".docx"):
            from docx import Document
            document = Document(io.BytesIO(file_data.read()))
            content = "\n".join([para.text for para in document.paragraphs])
        elif filename.endswith(".pdf"):
            reader = PyPDF2.PdfReader(io.BytesIO(file_data.read()))
            content = "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            raise ValueError("Unsupported file format. Use .txt, .docx, or .pdf")

        chunks = [
            {
                "page_content": content[i:i + 512],
                "metadata": {"source": filename}
            }
            for i in range(0, len(content), 512)
        ]
        return chunks

    except Exception as e:
        print(f"Error processing file: {e}")
        return []
    
    
    
    
    
# ===== Store Embeddings Locally =====
def store_embeddings(chunks, filename):
    rag_data = []

    for chunk in chunks:
        embedding = get_dummy_embedding(chunk["page_content"])
        doc = {
            "text": chunk["page_content"],
            "embedding": embedding.tolist(),
            "metadata": chunk["metadata"],
            "source_file": filename,
            "timestamp": datetime.utcnow().isoformat()
        }
        rag_data.append(doc)

    # Store Locally
    with open(STORAGE_PATH, "w") as f:
        json.dump(rag_data, f, indent=2)
    print(f"Stored {len(rag_data)} embeddings locally at {STORAGE_PATH}")

    return rag_data

# ===== Local Retriever =====
class LocalRetriever:
    def retrieve(self, query, top_k=3):
        query_embed = get_dummy_embedding(query)

        with open(STORAGE_PATH) as f:
            data = json.load(f)

        sim_scores = [
            cosine_similarity([query_embed], [np.array(item["embedding"])])[0][0]
            for item in data
        ]
        top_indices = np.argsort(sim_scores)[-top_k:][::-1]
        return [data[i] for i in top_indices]



# ===== Main Pipeline =====
async def main():
    
    retriever = LocalRetriever()

if __name__ == "__main__":
    asyncio.run(main())
