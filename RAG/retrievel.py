import os
import json
from dotenv import load_dotenv
import numpy as np
from pymongo import MongoClient
from bson.binary import Binary
import pickle
from datetime import datetime
from sklearn.metrics.pairwise import cosine_similarity
from langchain_google_vertexai import VertexAIEmbeddings, VertexAI
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    UnstructuredFileLoader,
)

from langchain.text_splitter import RecursiveCharacterTextSplitter

load_dotenv()

# ===== Configuration =====
# GEMINI_API_KEY = "AIzaSyBXkq2Nr0ftv9d4uXa7fcoiDOqu691CsBY"  # Replace with env var in production
# MONGO_URI = "mongodb+srv://<username>:<password>@cluster.mongodb.net/<dbname>?retryWrites=true&w=majority"
# LOCAL_STORAGE = "rag_embeddings"

# # ===== Initialize Services =====
# def setup_storage():
#     """Initialize storage systems"""
#     os.makedirs(LOCAL_STORAGE, exist_ok=True)
#     mongo_client = MongoClient(MONGO_URI)
#     return mongo_client["rag_database"]["embeddings_collection"]

# collection = setup_storage()

# Initialize Gemini with API key
os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")
embedding_model = VertexAIEmbeddings(
    model_name="textembedding-gecko@003",
    project="generative-ai-project",  # Your GCP project ID
    location="us-central1"
)

llm = VertexAI(
    model_name="gemini-1.5-flash",
    temperature=0.3,
    max_output_tokens=2048
)

# ===== Core Functions =====
def load_user_file(file_path):
    """Your existing document loader"""
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        if file_path.lower().endswith('.pdf'):
            loader = PyPDFLoader(file_path)
        elif file_path.lower().endswith('.docx'):
            loader = Docx2txtLoader(file_path)
        elif file_path.lower().endswith('.txt'):
            loader = TextLoader(file_path)
        else:
            loader = UnstructuredFileLoader(file_path)

        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=512,
            chunk_overlap=50,
            length_function=len,
            is_separator_regex=False,
        )
        return text_splitter.split_documents(documents)
    
    except Exception as e:
        print(f"Error loading {file_path}: {str(e)}")
        return []

def store_embeddings(chunks, filename):
    """Dual storage with local JSON and MongoDB"""
    rag_data = []
    
    for chunk in chunks:
        embedding = embedding_model.embed_query(chunk.page_content)
        doc = {
            "text": chunk.page_content,
            "embedding": Binary(pickle.dumps(np.array(embedding))),
            "metadata": chunk.metadata,
            "source_file": filename,
            "timestamp": datetime.utcnow()
        }
        rag_data.append(doc)
    
    # Local JSON storage
    local_path = os.path.join(LOCAL_STORAGE, f"{os.path.splitext(filename)[0]}.json")
    with open(local_path, "w") as f:
        json.dump([{**d, "embedding": d["embedding"].decode('latin1')} for d in rag_data], f, indent=2)
    
    # MongoDB storage
    collection.insert_many(rag_data)
    print(f"Stored {len(rag_data)} embeddings in both systems")
    return rag_data

class GeminiRetriever:
    def __init__(self, use_mongo=False):
        self.use_mongo = use_mongo
        
    def retrieve(self, query, top_k=3):
        if self.use_mongo:
            # MongoDB vector search
            query_embed = embedding_model.embed_query(query)
            results = list(collection.aggregate([
                {"$vectorSearch": {
                    "queryVector": pickle.dumps(np.array(query_embed)),
                    "path": "embedding",
                    "numCandidates": 100,
                    "limit": top_k,
                    "index": "vector_index"
                }}
            ]))
            return [{**r, "embedding": pickle.loads(r["embedding"])} for r in results]
        else:
            # Local JSON search
            with open(os.path.join(LOCAL_STORAGE, "embeddings.json")) as f:
                data = json.load(f)
                data = [{**d, "embedding": pickle.loads(d["embedding"].encode('latin1'))} for d in data]
                
            query_embed = embedding_model.embed_query(query)
            sim_scores = [
                cosine_similarity([query_embed], [np.array(item["embedding"])])[0][0]
                for item in data
            ]
            top_indices = np.argsort(sim_scores)[-top_k:][::-1]
            return [data[i] for i in top_indices]

# ===== Main Pipeline =====
if __name__ == "__main__":
    # 1. Load document
    file_path = input("Enter document path: ").strip()
    chunks = load_user_file(file_path)
    
    if not chunks:
        print("No valid chunks found. Exiting.")
        exit()
    
    # 2. Store embeddings
    filename = os.path.basename(file_path)
    store_embeddings(chunks, filename)
    
    # 3. Initialize retriever (toggle use_mongo=True for cloud)
    retriever = GeminiRetriever(use_mongo=False)
    
    # 4. Query loop
    while True:
        question = input("\nAsk a question (or 'quit'): ").strip()
        if question.lower() == 'quit':
            break
            
        results = retriever.retrieve(question)
        context = "\n\n".join(f"{r['text']}\n[Source: {r['metadata']['source']}]" for r in results)
        
        response = llm.invoke(
            f"Context:\n{context}\n\nQuestion: {question}\n"
            "Answer concisely with source citations:"
        )
        print(f"\nAnswer: {response}\n")