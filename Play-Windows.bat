@echo off
cd /d "%~dp0"
echo Open http://localhost:8000 after the server starts.
py -3 Tools\serve_game.py
pause
