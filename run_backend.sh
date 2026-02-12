#!/bin/bash
python -m backend.db_setup
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
