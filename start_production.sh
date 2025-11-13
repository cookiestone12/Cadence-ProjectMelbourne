#!/bin/bash
set -e

echo "Building frontend..."
cd frontend && npm run build && cd ..

echo "Starting production server on port 5000..."
python -m uvicorn backend.main:app --host 0.0.0.0 --port 5000
