@echo off
chcp 65001 >nul
title Chasseur de Concours
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Premiere installation, une minute...
  python -m venv .venv || (echo Python est introuvable. Installe-le depuis le Microsoft Store puis relance. & pause & exit /b)
  ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
)
netstat -ano | findstr ":8765" | findstr "LISTENING" >nul && (start "" http://127.0.0.1:8765/ & exit /b)
".venv\Scripts\python.exe" serveur.py
