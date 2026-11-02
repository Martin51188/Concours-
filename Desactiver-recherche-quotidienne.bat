@echo off
schtasks /Delete /F /TN "Chasseur de Concours" >nul 2>&1
echo Recherche quotidienne desactivee.
pause
