@echo off
setlocal

REM Step 1: Start RAG/main.py using uvicorn
echo Starting RAG/main.py server...
start "" cmd /k "uvicorn RAG.main:app --host 0.0.0.0 --port 8000"

REM Step 2: Wait for rag_ready.flag file
echo Waiting for rag_ready.flag to appear...
:wait_loop
if exist rag_ready.flag (
    echo Detected rag_ready.flag. Proceeding...
    goto next_step
) else (
    timeout /t 2 >nul
    goto wait_loop
)

:next_step
REM Step 3: Run LLM Procurement pipeline
echo Running src/llm_procurement/main.py...
python src/llm_procurement/main.py

REM Step 4: Run data pipeline
echo Running data/main.py server...
start "" cmd /k "uvicorn data.main:app --host 0.0.0.0 --port 8001"

echo All components launched.
pause
