#!/bin/bash

# --- Configuration ---
RAG_DIR="RAG"
RAG_PORT=8000
RAG_APP="main:app"
SIGNAL_FILE="$RAG_DIR/rag_ready.flag"

LLM_INFERENCE_DIR="src/llm_inference"
LLM_INFERENCE_SCRIPT="main.py"

DATA_DIR="data"
DATA_PORT=8001
DATA_APP="main:app"

WAIT_INTERVAL=5 # Seconds to wait between checking for the signal file
# --- End Configuration ---

# Store the final exit code
FINAL_EXIT_CODE=0

echo "--- Starting sequence ---"

# --- Preparations ---
echo "Checking for existing signal file..."
if [ -f "$SIGNAL_FILE" ]; then
    echo "Removing existing signal file: $SIGNAL_FILE"
    rm -f "$SIGNAL_FILE"
fi

# --- Step 1: Run RAG/main.py (FastAPI/Uvicorn) in Background ---
echo "[Step 1] Starting RAG server ($RAG_APP) on port $RAG_PORT in directory $RAG_DIR..."
pushd "$RAG_DIR" || {
    echo "Error: Directory '$RAG_DIR' not found."
    exit 1
}

# Start Uvicorn in background and save PID
nohup uvicorn $RAG_APP --host 0.0.0.0 --port $RAG_PORT --log-level info > rag_server.log 2>&1 &
RAG_PID=$!
echo "RAG server started in background (PID: $RAG_PID)"
echo "Waiting for RAG server to create signal file: $SIGNAL_FILE"

popd

# Give the server a moment to initialize before starting the check loop
sleep 3

# --- Step 2: Wait for Signal File ---
echo "Checking for signal file..."
while true; do
    if [ -f "$SIGNAL_FILE" ]; then
        echo "Signal file '$SIGNAL_FILE' found. Proceeding..."
        break
    fi

    # Check if the process is still running
    if ! kill -0 $RAG_PID 2>/dev/null; then
        echo "Error: RAG server process (PID: $RAG_PID) is not running."
        FINAL_EXIT_CODE=1
        break
    fi

    echo "Signal file not found yet. Waiting $WAIT_INTERVAL seconds..."
    sleep $WAIT_INTERVAL
done

if [ $FINAL_EXIT_CODE -ne 0 ]; then
    exit $FINAL_EXIT_CODE
fi

# --- Step 3: Run src/llm_inference/main.py ---
echo "[Step 3] Running LLM Inference script: python $LLM_INFERENCE_DIR/$LLM_INFERENCE_SCRIPT..."
python "$LLM_INFERENCE_DIR/$LLM_INFERENCE_SCRIPT"
if [ $? -ne 0 ]; then
    echo "Error: LLM Inference script failed with exit code $?."
    FINAL_EXIT_CODE=$?
    exit $FINAL_EXIT_CODE
fi
echo "LLM Inference script finished successfully."

# --- Step 4: Run data/main.py (FastAPI/Uvicorn) in Foreground ---
echo "[Step 4] Starting Data server ($DATA_APP) on port $DATA_PORT in directory $DATA_DIR..."
pushd "$DATA_DIR" || {
    echo "Error: Directory '$DATA_DIR' not found."
    exit 1
}

# Run this one in foreground
uvicorn $DATA_APP --host 0.0.0.0 --port $DATA_PORT --log-level info
FINAL_EXIT_CODE=$?
popd
echo "Data server stopped (Exit code: $FINAL_EXIT_CODE)."

# --- Cleanup ---
echo "--- Cleaning up ---"
if [ -f "$SIGNAL_FILE" ]; then
    echo "Removing signal file: $SIGNAL_FILE"
    rm -f "$SIGNAL_FILE"
fi

# Kill RAG server if still running
if kill -0 $RAG_PID 2>/dev/null; then
    echo "Stopping RAG server (PID: $RAG_PID)..."
    kill $RAG_PID
fi

echo
echo "****************************************************************"
echo "NOTE: The RAG server ($RAG_APP) was started in background."
echo "Logs can be found in: $RAG_DIR/rag_server.log"
echo "****************************************************************"
echo
echo "--- Sequence finished ---"

exit $FINAL_EXIT_CODE