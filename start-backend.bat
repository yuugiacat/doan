@echo off
set PYTHONPATH=d:\demoapp\backend
"C:\Users\Admin\AppData\Local\Programs\Python\Python313\python.exe" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
