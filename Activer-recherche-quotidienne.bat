@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (echo Lance d'abord Lancer.bat une fois. & pause & exit /b)
schtasks /Create /F /SC DAILY /ST 18:00 /TN "Chasseur de Concours" /TR "\"%~dp0.venv\Scripts\pythonw.exe\" \"%~dp0agent.py\" --notifier" >nul
if errorlevel 1 (echo La tache n'a pas pu etre creee. & pause & exit /b)
echo C'est fait : l'agent cherchera les nouveaux concours tous les jours a 18h
echo et t'enverra une notification s'il en trouve.
echo (Pour arreter : lance Desactiver-recherche-quotidienne.bat)
pause
