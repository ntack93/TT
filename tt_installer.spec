# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Add this for better debugging
a = Analysis(
    ['TT/main.py'],
    pathex=['c:\\Users\\Noah\\OneDrive\\Documents\\TT'],
    binaries=[],
    datas=[
        ('TT/chat.wav', 'TT'),
        ('TT/directed.wav', 'TT'),
        ('TT/init_config.py', 'TT'),
        ('TT/ASCII_EXT.py', 'TT'),
        ('TT/image_patch.py', 'TT'),
    ],
    hiddenimports=[
        'PIL', 'PIL._tkinter_finder', 'PIL._imaging', 'PIL.Image', 'PIL.ImageTk',
        'PIL.ImageFile', 'PIL.GifImagePlugin', 'PIL.PngImagePlugin', 'PIL.JpegImagePlugin',
        'enchant', 'asyncio', 'telnetlib3', 'tkinter', 'tkinter.ttk',
        'tkinter.filedialog', 'tkinter.messagebox', 'winsound', 'queue', 
        'json', 'webbrowser', 'sys', 'requests', 'urllib3', 'certifi', 'idna', 'chardet',
        'io', 'traceback', 'shutil', 'tempfile', 'pathlib',
        'vlc'
    ],
    hookspath=['.'],  # Look for hooks in current directory
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
    console=True,  # Keep True for debugging
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
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