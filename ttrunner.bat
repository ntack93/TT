@echo off
:: Teleconference Terminal Build Script
echo Building Teleconference Terminal...
echo.

echo Step 1: Clean previous builds
rmdir /s /q "dist\TeleconferenceTerminal" 2>nul
rmdir /s /q "build\tt_installer" 2>nul

echo Step 2: Ensure PIL is properly installed
py -3.12 -m pip install --upgrade pillow

echo Step 3: Building with PyInstaller (Python 3.12)
py -3.12 -m PyInstaller tt_installer.spec

echo Step 4: Checking build output
if not exist "dist\TeleconferenceTerminal\TeleconferenceTerminal.exe" (
  echo Build failed: Executable not found
  exit /b 1
)

echo Step 5: Copying sound files
copy "TT\chat.wav" "dist\TeleconferenceTerminal\" /y
copy "TT\directed.wav" "dist\TeleconferenceTerminal\" /y
mkdir "dist\TeleconferenceTerminal\_internal" 2>nul
copy "TT\chat.wav" "dist\TeleconferenceTerminal\_internal\" /y
copy "TT\directed.wav" "dist\TeleconferenceTerminal\_internal\" /y

echo Step 5a: Copying VLC files from installation
set VLC_PATH=C:\Program Files\VideoLAN\VLC
if not exist "%VLC_PATH%" (
  echo ERROR: VLC not found at %VLC_PATH%. Please install VLC or update the path.
  exit /b 1
)
copy "%VLC_PATH%\libvlc.dll" "dist\TeleconferenceTerminal\" /y
copy "%VLC_PATH%\libvlccore.dll" "dist\TeleconferenceTerminal\" /y
mkdir "dist\TeleconferenceTerminal\plugins" 2>nul
xcopy "%VLC_PATH%\plugins\*" "dist\TeleconferenceTerminal\plugins\" /s /e /y

echo Step 6: Creating redist directory
mkdir "redist" 2>nul

echo Step 7: Checking for VC++ Redistributable files
if not exist "redist\vc_redist.x86.exe" (
  echo WARNING: VC++ Redistributable x86 missing from redist folder
  echo Download from: https://aka.ms/vs/17/release/vc_redist.x86.exe
)

if not exist "redist\vc_redist.x64.exe" (
  echo WARNING: VC++ Redistributable x64 missing from redist folder
  echo Download from: https://aka.ms/vs/17/release/vc_redist.x64.exe
)

echo Step 8: Fixing permissions
icacls "dist\TeleconferenceTerminal\*" /grant Everyone:(OI)(CI)F

echo Step 9: Building installer with InnoSetup
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" setup.iss

echo Build process complete!
if exist "Output\TeleconferenceTerminal_Setup.exe" (
  echo Installer created successfully at: Output\TeleconferenceTerminal_Setup.exe
) else (
  echo WARNING: Installer may not have been created successfully
)