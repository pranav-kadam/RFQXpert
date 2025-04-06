from fastapi import FastAPI
from fastapi.responses import FileResponse
import os
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Restrict to your frontend in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

@app.get("/check")
def get_checklist_output():
    filepath = os.path.join("data", "checklist_output.json")
    if os.path.exists(filepath):
        return FileResponse(filepath, media_type="application/json")
    return {"error": "File not found"}
