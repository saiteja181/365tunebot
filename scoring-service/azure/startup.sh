#!/bin/bash

# Azure App Service Startup Script for Security Scoring Service

echo "Starting Security Scoring Service..."
echo "Python version: $(python --version)"

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Start the service
echo "Starting FastAPI application..."
python -m uvicorn app:app --host 0.0.0.0 --port ${PORT:-8001}
