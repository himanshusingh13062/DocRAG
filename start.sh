#!/bin/bash

# Start FastAPI backend in background
echo "Starting FastAPI backend on port 8000..."
cd /app
python main.py &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend to start..."
timeout=30
count=0
while ! curl -f http://localhost:8000/health/ >/dev/null 2>&1; do
    sleep 2
    count=$((count + 2))
    if [ $count -ge $timeout ]; then
        echo "Backend failed to start within $timeout seconds"
        kill $BACKEND_PID 2>/dev/null
        exit 1
    fi
    echo "Waiting for backend... ($count/$timeout seconds)"
done

echo "Backend is ready!"

# Start Streamlit frontend
echo "Starting Streamlit frontend on port 8501..."
streamlit run app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false

# If we reach here, streamlit exited, so kill backend
echo "Streamlit exited, cleaning up..."
kill $BACKEND_PID 2>/dev/null