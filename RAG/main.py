from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from retrievel import load_user_file, store_embeddings
import os

app = FastAPI()


DATA = os.path.join("data")
os.makedirs(DATA, exist_ok=True)


# @app.post("/upload")
# async def upload_file(file: UploadFile = File(...)):
#     content = await file.read()
#     return {
#         "filename": file.filename,
#         "content_size": len(content)
#     }

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Save the file temporarily
        file_path = os.path.join(DATA, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Re-open as a file-like object for processing
        with open(file_path, "rb") as f:
            chunks = load_user_file(f, file.filename)

        if not chunks:
            return JSONResponse(content={"error": "File could not be processed or was empty."}, status_code=400)

        store_embeddings(chunks, file.filename)

        return {"message": f"{file.filename} uploaded and embeddings stored successfully."}

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
