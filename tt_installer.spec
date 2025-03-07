# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['TT/main.py'],  # Main script path
    pathex=['c:\\Users\\Noah\\OneDrive\\Documents\\TT'],  # Update this to your actual path
    binaries=[],
    datas=[
        ('TT/chat.wav', 'TT'),  # Include sound files in TT subfolder
        ('TT/directed.wav', 'TT'),
        ('TT/ASCII_EXT.py', 'TT'),
        ('TT/init_config.py', 'TT'),
        ('TT/image_patch.py', 'TT'),  # Make sure this file exists
    ],
    hiddenimports=[
        'PIL', 'PIL._imaging', 'PIL.Image', 'PIL.ImageTk', 'PIL._tkinter_finder',
        'enchant', 'asyncio', 'telnetlib3', 'tkinter', 'tkinter.ttk', 
        'winsound', 'queue', 'json', 'webbrowser', 'sys', 'requests'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['runtime_hook.py'],  # Include runtime hook
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TeleconferenceTerminal',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to False for a windowed application
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)