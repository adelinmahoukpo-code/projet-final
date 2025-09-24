@echo off
echo ================================
echo 🚀 Démarrage du serveur Flask
echo ================================
cd /d "%~dp0"
echo Dossier actuel: %CD%
echo.
echo Démarrage du serveur...
python serveur.py
pause