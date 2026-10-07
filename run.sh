#!/bin/bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
PYTHONUNBUFFERED=1 python3 app.py
