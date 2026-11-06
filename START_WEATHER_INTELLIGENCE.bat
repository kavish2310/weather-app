@echo off
cd /d "%~dp0"
python run_weather_intelligence.py
if errorlevel 1 (
  echo.
  echo Weather Intelligence could not start.
  echo Make sure Python and the packages in requirements.txt are installed.
  pause
)
