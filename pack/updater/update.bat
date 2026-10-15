@echo off
setlocal
set "GIT_BASH=%ProgramFiles%\Git\bin\bash.exe"
if not exist "%GIT_BASH%" set "GIT_BASH=%ProgramFiles(x86)%\Git\bin\bash.exe"
if not exist "%GIT_BASH%" (
  for /f "delims=" %%G in ('where git.exe 2^>nul') do (
    if exist "%%~dpG..\bin\bash.exe" set "GIT_BASH=%%~dpG..\bin\bash.exe"
    if exist "%%~dpGbash.exe" set "GIT_BASH=%%~dpGbash.exe"
  )
)
if not exist "%GIT_BASH%" (
  echo Please install Git for Windows from https://gitforwindows.org/
  pause
  exit /b 1
)
"%GIT_BASH%" --login "%~dp0expedition-update.sh" %*
set "UPDATE_RC=%ERRORLEVEL%"
if not "%UPDATE_RC%"=="0" echo Update stopped. See the message and .expedition/logs/.
pause
exit /b %UPDATE_RC%
