#!/bin/bash
# SewerSentinel Setup Script
# Sets up the development environment for the project

set -e  # Exit on error

echo "================================================"
echo "     SewerSentinel Setup"
echo "     Autonomous Infrastructure Prediction System"
echo "================================================"
echo ""

# Check Python version
echo "Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "ERROR: Python not found. Please install Python 3.10+"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
echo "Found Python $PYTHON_VERSION"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
    echo "Virtual environment created."
else
    echo "Virtual environment already exists."
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Check for GEMINI_API_KEY
echo ""
echo "Checking for API key..."
if [ -z "$GEMINI_API_KEY" ]; then
    echo ""
    echo "WARNING: GEMINI_API_KEY environment variable is not set."
    echo ""
    echo "To set it, run one of the following:"
    echo "  export GEMINI_API_KEY='your-api-key'   (Linux/Mac)"
    echo "  set GEMINI_API_KEY=your-api-key        (Windows CMD)"
    echo "  \$env:GEMINI_API_KEY='your-api-key'    (Windows PowerShell)"
    echo ""
    echo "You can get an API key from: https://aistudio.google.com/app/apikey"
else
    echo "GEMINI_API_KEY is configured."
fi

# Create data directory if it doesn't exist
echo ""
echo "Creating data directory..."
mkdir -p data/sample

echo ""
echo "================================================"
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Set your GEMINI_API_KEY environment variable"
echo "  2. Run './run.sh' to start the application"
echo "  3. Or run 'streamlit run aistudio_app.py' for the demo app"
echo "================================================"
