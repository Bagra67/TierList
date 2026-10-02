@echo off
rem Lance dev.ps1 sans dépendre de la politique d'exécution PowerShell de la machine
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev.ps1" %*
