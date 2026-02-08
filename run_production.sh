#!/bin/bash
set -e

echo "Building frontend..."
cd frontend && npm run build && cd ..

echo "Starting production server..."
gunicorn backend.main:app -c backend/gunicorn_config.py
