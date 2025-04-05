from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="RFP Analysis System with Gemini",
    version="2.0",
    docs_url="/api/docs",
    redoc_url=None
)


@app.on_event("startup")
async def startup_event():
    # Initialize Gemini client
    from llm_inference.utils.gemini import gemini_client
    try:
        # Test connection
        await gemini_client.generate_content("Test connection")
        print("Gemini connection successful")
    except Exception as e:
        print(f"Gemini connection failed: {str(e)}")