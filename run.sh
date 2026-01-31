#!/bin/bash
# SewerSentinel Run Script
# Starts the backend server (and optionally the frontend)

set -e  # Exit on error

echo "================================================"
echo "     SewerSentinel"
echo "     Autonomous Infrastructure Prediction System"
echo "================================================"
echo ""

# Check for virtual environment
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        source venv/Scripts/activate
    else
        source venv/bin/activate
    fi
else
    echo "WARNING: Virtual environment not found."
    echo "Run './setup.sh' first to set up the project."
fi

# Check for GEMINI_API_KEY
if [ -z "$GEMINI_API_KEY" ]; then
    echo ""
    echo "WARNING: GEMINI_API_KEY is not set."
    echo "The API will run in demo mode with limited functionality."
    echo ""
    echo "To set it: export GEMINI_API_KEY='your-api-key'"
    echo ""
fi

# Parse command line arguments
MODE="${1:-api}"

case $MODE in
    "api")
        echo "Starting SewerSentinel API Server..."
        echo ""
        echo "API will be available at: http://localhost:8000"
        echo "API Docs: http://localhost:8000/docs"
        echo "Health Check: http://localhost:8000/api/health"
        echo ""
        echo "Press Ctrl+C to stop the server."
        echo ""
        python -m uvicorn server:app --reload --host 0.0.0.0 --port 8000
        ;;

    "streamlit")
        echo "Starting SewerSentinel Streamlit App..."
        echo ""
        echo "App will be available at: http://localhost:8501"
        echo ""
        echo "Press Ctrl+C to stop the app."
        echo ""
        streamlit run aistudio_app.py --server.port 8501
        ;;

    "both")
        echo "Starting both API Server and Streamlit App..."
        echo ""
        echo "API: http://localhost:8000"
        echo "Streamlit: http://localhost:8501"
        echo ""
        # Start API in background
        python -m uvicorn server:app --host 0.0.0.0 --port 8000 &
        API_PID=$!

        # Wait a moment for API to start
        sleep 2

        # Start Streamlit
        streamlit run aistudio_app.py --server.port 8501

        # When Streamlit exits, kill API
        kill $API_PID 2>/dev/null
        ;;

    *)
        echo "Usage: ./run.sh [mode]"
        echo ""
        echo "Modes:"
        echo "  api       - Start the FastAPI backend server (default)"
        echo "  streamlit - Start the Streamlit demo app"
        echo "  both      - Start both API and Streamlit"
        ;;
esac
