
Running in a separate Windows Command Prompt
If you don't have Docker, run it in a standalone command line window:

Open PowerShell or Command Prompt directly from your Windows Start menu.
Navigate to your project folder:
powershell
cd "d:\SecurePrompt AI"
Activate the environment:
powershell
.\venv\Scripts\Activate.ps1
Start the server:
powershell
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
