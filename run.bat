@echo off
setlocal

REM --- Configuration ---
set RAG_DIR=RAG
set RAG_PORT=8000
set RAG_APP=main:app
set SIGNAL_FILE=%RAG_DIR%\rag_ready.flag

set LLM_INFERENCE_DIR=src\llm_inference
set LLM_INFERENCE_SCRIPT=main.py

set DATA_DIR=data
set DATA_PORT=8001
set DATA_APP=main:app

set WAIT_INTERVAL=5 REM Seconds to wait between checking for the signal file
REM --- End Configuration ---

REM Store the final exit code
set FINAL_EXIT_CODE=0

echo --- Starting sequence ---

REM --- Preparations ---
echo Checking for existing signal file...
if exist "%SIGNAL_FILE%" (
    echo Removing existing signal file: %SIGNAL_FILE%
    del /Q "%SIGNAL_FILE%"
)

REM --- Step 1: Run RAG/main.py (FastAPI/Uvicorn) in a New Window ---
echo [Step 1] Starting RAG server (%RAG_APP%) on port %RAG_PORT% in directory %RAG_DIR%...
pushd "%RAG_DIR%" || (
    echo Error: Directory '%RAG_DIR%' not found.
    goto ErrorExit
)
REM Start Uvicorn in a new window. Give it a title for identification.
REM cmd /c keeps the window open until uvicorn stops OR the window is closed.
start "RAG Server - %RAG_APP%" cmd /c "uvicorn %RAG_APP% --host 0.0.0.0 --port %RAG_PORT% --log-level info"
popd
echo RAG server starting in a new window.
echo Waiting for RAG server to create signal file: %SIGNAL_FILE%

REM Give the server a moment to initialize before starting the check loop
timeout /t 3 /nobreak > nul

REM --- Step 2: Wait for Signal File ---
echo Checking for signal file...
:WaitLoop
if exist "%SIGNAL_FILE%" (
    echo Signal file '%SIGNAL_FILE%' found. Proceeding...
    goto Step3
)

REM Optional: Check if the process is still running (difficult and unreliable in pure batch)
REM We'll just rely on the file appearing or the user manually intervening.

echo Signal file not found yet. Waiting %WAIT_INTERVAL% seconds...
timeout /t %WAIT_INTERVAL% /nobreak > nul
goto WaitLoop


:Step3
REM Optional: Delete the signal file now? Or leave it for cleanup.
REM if exist "%SIGNAL_FILE%" del /Q "%SIGNAL_FILE%"

REM --- Step 3: Run src/llm_inference/main.py ---
echo [Step 3] Running LLM Inference script: python "%LLM_INFERENCE_DIR%\%LLM_INFERENCE_SCRIPT%"...
python "%LLM_INFERENCE_DIR%\%LLM_INFERENCE_SCRIPT%"
if %ERRORLEVEL% NEQ 0 (
    echo Error: LLM Inference script failed with exit code %ERRORLEVEL%.
    set FINAL_EXIT_CODE=%ERRORLEVEL%
    goto Cleanup
)
echo LLM Inference script finished successfully.

REM --- Step 4: Run data/main.py (FastAPI/Uvicorn) in Foreground ---
echo [Step 4] Starting Data server (%DATA_APP%) on port %DATA_PORT% in directory %DATA_DIR%...
pushd "%DATA_DIR%" || (
    echo Error: Directory '%DATA_DIR%' not found.
    goto ErrorExit
)
REM Run this one directly in the current window. Script waits here.
uvicorn %DATA_APP% --host 0.0.0.0 --port %DATA_PORT% --log-level info
set FINAL_EXIT_CODE=%ERRORLEVEL%
popd
echo Data server stopped (Exit code: %FINAL_EXIT_CODE%).

goto Cleanup

:ErrorExit
echo Script aborted due to error.
set FINAL_EXIT_CODE=1
goto Cleanup

:Cleanup
echo --- Cleaning up ---
if exist "%SIGNAL_FILE%" (
    echo Removing signal file: %SIGNAL_FILE%
    del /Q "%SIGNAL_FILE%"
)

echo.
echo ****************************************************************
echo NOTE: The RAG server (%RAG_APP%) was started in a separate window.
echo If it is still running, please close its window manually.
echo ****************************************************************
echo.
echo --- Sequence finished ---

endlocal
exit /b %FINAL_EXIT_CODE%