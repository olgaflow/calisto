@echo off
cd /d "%~dp0"

echo Installation de PyInstaller...
python -m pip install -q --upgrade pyinstaller
if errorlevel 1 (
    echo Impossible d'installer PyInstaller.
    pause
    exit /b 1
)

echo Construction de Calisto...
python -m PyInstaller --noconfirm --clean calisto.spec
if errorlevel 1 (
    echo Echec de la construction.
    pause
    exit /b 1
)

echo.
echo Termine : dist\Calisto\Calisto.exe
echo Copiez le dossier dist\Calisto sur le poste ou vous voulez installer l'application.
pause
