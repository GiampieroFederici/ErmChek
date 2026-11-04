@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0installa_ermchek.ps1"
if errorlevel 1 pause
