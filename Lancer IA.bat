@echo off
cd /d "%~dp0"

echo Installation/verification des dependances...
python -m pip install -q ddgs ollama PyPDF2 customtkinter tkinterweb 2>nul
if errorlevel 1 (
    echo Erreur lors de l'installation des dependances.
    pause
    exit /b 1
)

echo Lancement de Calisto...
start "" python app_desktop.py
