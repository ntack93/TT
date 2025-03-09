@echo off
:: filepath: c:\Users\Noah\OneDrive\Documents\TT\build.bat
echo Building Teleconference Terminal...
echo.

echo Step 1: Clean previous builds
rmdir /s /q "dist\TeleconferenceTerminal" 2>nul
rmdir /s /q "build\tt_installer" 2>nul

echo Step 2: Building with PyInstaller
pyinstaller tt_installer.spec

echo Step 3: Checking build output
if not exist "dist\TeleconferenceTerminal\TeleconferenceTerminal.exe" (
  echo Build failed: Executable not found
  exit /b 1
)

echo Step 4: Fixing permissions
icacls "dist\TeleconferenceTerminal\*" /grant Everyone:(OI)(CI)F

echo Step 5: Building installer with InnoSetup
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" setup.iss

echo Build process complete!