#!/bin/sh
pip install -r requirements.txt --break-system-packages 2>/dev/null || pip install -r requirements.txt
python3 -m uvicorn rcd.api:app --host 127.0.0.1 --port 8000
