# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['TT/main.py'],            # The main Python script
    pathex=['c:\\buildproject'],
    binaries=[],
    datas=[
        ('TT/chat.wav', '.'),
        ('TT/directed.wav', '.'),
        ('TT/init_config.py', 'TT'),
        ('TT/ASCII_EXT.py', 'TT'),
        ('TT/image_patch.py', 'TT'),  # Make sure patch file is included
    ],
    hiddenimports=[
        'PIL',
        'PIL._tkinter_finder', 
        'PIL._imaging',
        'PIL.Image', 
        'PIL.ImageTk',
        'enchant', 
        'asyncio', 
        'telnetlib3', 
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'winsound', 
        'queue', 
        'json', 
        'webbrowser', 
        'sys',
        'requests',
        'urllib3',
        'chardet',
        'idna',
        'certifi',
        'io',
        'traceback',
        'shutil',
        'tempfile',
        'pathlib',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['runtime_hook.py'],  # Add the runtime hook
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
    console=True,  # Keep True for debugging
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)