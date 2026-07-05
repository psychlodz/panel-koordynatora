@echo off
chcp 65001 >nul
setlocal

echo =====================================
echo Building KOMPAS application
echo Entry point: main.py
echo =====================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found in PATH.
    echo Install Python 3.11 or 3.12 and select Add Python to PATH.
    pause
    exit /b 1
)

for /f "delims=" %%i in ('python -c "import version; print(version.APP_NAME)"') do set "APP_NAME=%%i"
if errorlevel 1 goto error
for /f "delims=" %%i in ('python -c "import version; print(version.VERSION)"') do set "APP_VERSION=%%i"
if errorlevel 1 goto error
for /f "delims=" %%i in ('python -c "import version; print(version.BUILD)"') do set "APP_BUILD=%%i"
if errorlevel 1 goto error

if not defined APP_NAME goto error
if not defined APP_VERSION goto error
if not defined APP_BUILD goto error

set "RELEASE_DIR=release\%APP_NAME%_%APP_VERSION%"

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "%RELEASE_DIR%" rmdir /s /q "%RELEASE_DIR%"

python -m pip install -r requirements.txt
if errorlevel 1 goto error

python -m PyInstaller --clean --noconfirm plan_pracy.spec
if errorlevel 1 goto error

if not exist release mkdir release
if not exist "%RELEASE_DIR%" mkdir "%RELEASE_DIR%"

xcopy "dist\%APP_NAME%\*" "%RELEASE_DIR%\" /E /I /Y >nul
if errorlevel 1 goto error

copy /Y "config.ini" "%RELEASE_DIR%\config.ini" >nul
if errorlevel 1 goto error

(
    echo APP_NAME=%APP_NAME%
    echo VERSION=%APP_VERSION%
    echo BUILD=%APP_BUILD%
) > "%RELEASE_DIR%\VERSION.txt"

echo.
echo Done.
echo EXE file: %RELEASE_DIR%\%APP_NAME%.exe
echo Release directory: %RELEASE_DIR%
echo.
pause
exit /b 0

:error
echo.
echo Build failed.
echo Check messages above.
pause
exit /b 1
