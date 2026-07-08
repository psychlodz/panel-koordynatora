@echo off
chcp 65001 >nul
setlocal

echo =====================================
echo Building KOMPAS installer
echo =====================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found in PATH.
    echo Install Python and select Add Python to PATH.
    pause
    exit /b 1
)

for /f "delims=" %%i in ('python -c "import version; print(version.APP_NAME)"') do set "APP_NAME=%%i"
if errorlevel 1 goto error
for /f "delims=" %%i in ('python -c "import version; print(version.VERSION)"') do set "APP_VERSION=%%i"
if errorlevel 1 goto error

set "RELEASE_DIR=release\%APP_NAME%_%APP_VERSION%"
set "INSTALLER_DIR=release\installers"
set "INNO_SCRIPT=installer\KOMPAS.iss"

call build_exe.bat
if errorlevel 1 goto error

if not exist "%RELEASE_DIR%\%APP_NAME%.exe" (
    echo Missing release executable: %RELEASE_DIR%\%APP_NAME%.exe
    goto error
)

if not exist "%RELEASE_DIR%\VERSION.txt" (
    echo Missing release version file: %RELEASE_DIR%\VERSION.txt
    goto error
)

if not exist "%RELEASE_DIR%\config.example.ini" (
    echo Missing release config template: %RELEASE_DIR%\config.example.ini
    goto error
)

where ISCC >nul 2>nul
if not errorlevel 1 (
    set "ISCC=ISCC"
    goto compile
)

if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
    set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    goto compile
)

if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" (
    set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
    goto compile
)

echo Inno Setup compiler ISCC.exe was not found.
echo Install Inno Setup 6 or add ISCC.exe to PATH.
goto error

:compile
if not exist "%INSTALLER_DIR%" mkdir "%INSTALLER_DIR%"

"%ISCC%" "%INNO_SCRIPT%"
if errorlevel 1 goto error

if not exist "%INSTALLER_DIR%\%APP_NAME%_Setup_%APP_VERSION%.exe" (
    echo Installer was not created:
    echo %INSTALLER_DIR%\%APP_NAME%_Setup_%APP_VERSION%.exe
    goto error
)

echo.
echo Done.
echo Installer: %INSTALLER_DIR%\%APP_NAME%_Setup_%APP_VERSION%.exe
echo.
pause
exit /b 0

:error
echo.
echo Installer build failed.
echo Check messages above.
pause
exit /b 1
