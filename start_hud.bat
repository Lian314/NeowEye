@echo off
cd /d "%~dp0"
title Slay the Spire Tactical Assistant
start "" "C:\Users\Admin\.local\bin\python3.12.exe" main.py --mode mock
