@echo off
rem Magical Chase installer for Windows.
rem   install.bat                         asks for the source and the folder
rem   install.bat D: C:\Games\MagicalChase [--japanese] [--portable] ...
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
  goto done
)
set "SRC=%~1"
if "%SRC%"=="" set /p "SRC=Disc drive (e.g. D:) or .cue / .iso file: "
set "OUT="
set /p "OUT=Install folder [%USERPROFILE%\Games\MagicalChase]: "
if "%OUT%"=="" set "OUT=%USERPROFILE%\Games\MagicalChase"
set "OPTS="
set "ANS="
set /p "ANS=Keep the original Japanese menus? (y/N): "
if /i "%ANS%"=="y" set "OPTS=%OPTS% --japanese"
set "ANS="
set /p "ANS=Save settings in the game folder (portable)? (y/N): "
if /i "%ANS%"=="y" set "OPTS=%OPTS% --portable"
%PY% "%HERE%patcher\install_magical_chase.py" "%SRC%" "%OUT%" %OPTS%
if not errorlevel 1 echo. & echo Start the game with "%OUT%\Mchase.exe"
:done
pause
