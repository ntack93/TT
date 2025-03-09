# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['TT/main.py'],
    pathex=['c:\\Users\\Noah\\OneDrive\\Documents\\TT'],
    binaries=[],
    datas=[
        ('TT/chat.wav', '.'),
        ('TT/directed.wav', '.'),
        ('TT/init_config.py', 'TT'),
        ('TT/ASCII_EXT.py', 'TT'),
        ('TT/image_patch.py', 'TT'),
    ],
    hiddenimports=[
        'PIL', 'PIL._tkinter_finder', 'PIL._imaging', 'PIL.Image', 'PIL.ImageTk',
        'enchant', 'asyncio', 'telnetlib3', 'tkinter', 'tkinter.ttk',
        'tkinter.filedialog', 'tkinter.messagebox', 'winsound', 'queue', 
        'json', 'webbrowser', 'sys', 'requests', 'urllib3', 'certifi', 'idna', 'chardet',
        'io', 'traceback', 'shutil', 'tempfile', 'pathlib',
        'vlc', 'python-vlc', 'urllib3.contrib', 'urllib3.contrib.socks',
        'urllib3.util', 'urllib3.connection', 'urllib3.response',
        'requests.adapters', 'requests.auth', 'requests.cookies', 
        'requests.models', 'requests.hooks', 'requests.structures',
        'threading', 'time',
    ],
    hookspath=['.'],
    hooksconfig={},
    runtime_hooks=['runtime_hook.py'],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TeleconferenceTerminal',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Change to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Remove the icon line since you don't have an icon file
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TeleconferenceTerminal',
)