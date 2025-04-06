import os
import io
import json
import asyncio
from datetime import datetime
from typing import List, Dict
import numpy as np
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
import PyPDF2
from docx import Document  # For handling .docx files

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()

# ===== Configuration =====
DATA_DIR = os.path.join(os.getcwd(), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Use fixed filenames for storage
STORAGE_PATH = os.path.join(DATA_DIR, "embeddings.json")
TEXT_STORAGE_PATH = os.path.join(DATA_DIR, "embedding.json")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FLAG_FILE = 'rag_ready.flag' # Relative to RAG directory
if not os.path.exists(FLAG_FILE):
    try:
        # Ensure directory exists if needed, though here it's in the CWD
        # os.makedirs(os.path.dirname(FLAG_FILE), exist_ok=True)
        with open(FLAG_FILE, 'w') as f:
            f.write('ready') # Content doesn't matter
        print(f"Created signal file: {FLAG_FILE}")
    except Exception as e:
        print(f"Error creating signal file {FLAG_FILE}: {e}")

# ===== Gemini Client =====
class GeminiClient:
    def __init__(self):
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("The 'google-generativeai' module is not installed. Please install it using 'pip install google-generativeai'.")
        
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

# Initialize Gemini client
gemini_client = GeminiClient()

# ===== Extract Text from File =====
def extract_text_from_file(file_data, filename: str) -> str:
    """Extract text content from different file types."""
    filename = filename.lower()
    
    try:
        if filename.endswith(".txt"):
            return file_data.decode("utf-8")
        elif filename.endswith(".docx"):
            document = Document(io.BytesIO(file_data))
            return "\n".join([para.text for para in document.paragraphs])
        elif filename.endswith(".pdf"):
            reader = PyPDF2.PdfReader(io.BytesIO(file_data))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            raise ValueError("Unsupported file format. Use .txt, .docx, or .pdf")
    except Exception as e:
        print(f"Error extracting text: {e}")
        return ""

# ===== Universal File Loader =====
def load_user_file(text_content, source_name: str) -> List[Dict]:
    try:
        chunks = [
            {
                "page_content": text_content[i:i + 512],
                "metadata": {"source": source_name}
            }
            for i in range(0, len(text_content), 512)
        ]
        return chunks
    except Exception as e:
        print(f"Error processing content: {e}")
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

# ===== FastAPI Application =====
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Restrict to your frontend in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Validate file type
        if not file.filename.lower().endswith(('.pdf', '.txt', '.docx')):
            return JSONResponse(
                status_code=400,
                content={"error": "Only PDF, TXT, and DOCX files are allowed"}
            )
        
        # Read file content
        content = await file.read()
        
        # Extract text from the file
        text_content = extract_text_from_file(content, file.filename)
        
        if not text_content:
            return JSONResponse(
                status_code=400,
                content={"error": "Could not extract text from file or file was empty."}
            )
        
        with open(TEXT_STORAGE_PATH, "w", encoding="utf-8") as f:
            json.dump({"text": text_content}, f, ensure_ascii=False, indent=2)

        
        # Process the text content into chunks
        chunks = load_user_file(text_content, "embedding.json")
        
        if not chunks:
            return JSONResponse(
                status_code=400,
                content={"error": "File could not be processed or was empty."}
            )
        
        # Store embeddings
        store_embeddings(chunks, "embedding.json")
        print("Successfully Parsed")
        return JSONResponse(
            status_code=200,
            content={"message": f"File converted to text and processed successfully as embeddings.txt"}
        )
    
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": f"Server error: {str(e)}"}
        )

@app.get("/")
async def root():
    return {"message": "File Processing API is running"}

# ===== Main execution =====
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)