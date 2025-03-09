from PyInstaller.utils.hooks import collect_all

# This tells PyInstaller to gather all vlc-related files
datas, binaries, hiddenimports = collect_all('vlc')

# Make sure python-vlc is explicitly listed
hiddenimports.append('python-vlc')