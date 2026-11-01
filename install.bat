@echo off
rem Ripple's Potion - Magical Chase installer for Windows.
rem   install.bat                          opens the installer window
rem   install.bat D: C:\Games\MagicalChase [--japanese] [--registry] [--disc-wav] [--numpad]
rem You can also drag a .cue file (or the disc drive) onto this file.
setlocal
set "HERE=%~dp0"
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo Python 3 is needed: https://www.python.org/downloads/
  echo Tick "Add python.exe to PATH" during setup, then run this again.
  pause
  exit /b 1
)
if not "%~2"=="" (
  %PY% "%HERE%patcher\install_magical_chase.py" %*
  pause
  exit /b
)
rem graphical installer; exit code 3 means tkinter is missing: ask in text
%PY% "%HERE%patcher\gui.py" %1
if not errorlevel 3 exit /b
%PY% "%HERE%patcher\install_magical_chase.py" --ask %1
pause
