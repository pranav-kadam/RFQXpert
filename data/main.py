from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/data")
async def get_data():
    filepath = "checklist_output.json"
    print(f"Reading file: {filepath} (last modified: {time.ctime(os.path.getmtime(filepath))})")
    
    with open(filepath, "r") as f:
        data = json.load(f)
    
    return data
