@echo off
echo.
echo ================================================
echo    SYSTEME DE DISTRIBUTION DES FACTURES IMPOTS
echo              DEMARRAGE DU SERVEUR
echo ================================================
echo.

cd /d "%~dp0"
echo Repertoire de travail: %CD%

echo.
echo Verification des fichiers necessaires...
if not exist "serveur.py" (
    echo ERREUR: serveur.py non trouve!
    pause
    exit /b 1
)

if not exist ".env" (
    echo ERREUR: fichier .env non trouve!
    echo Creez le fichier .env avec:
    echo GMAIL_USERNAME=votre-email@gmail.com
    echo GMAIL_PASSWORD=votre-mot-de-passe-app
    pause
    exit /b 1
)

echo ✓ Tous les fichiers sont presents

echo.
echo Demarrage du serveur Flask...
py serveur.py

echo.
echo Serveur arrete. Appuyez sur une touche pour continuer...
pause