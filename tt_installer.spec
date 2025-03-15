# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Define VLC path - adjust this to your VLC installation path
vlc_path = 'C:\\Program Files\\VideoLAN\\VLC'

# Add VLC binaries
vlc_binaries = [
    (os.path.join(vlc_path, 'libvlc.dll'), '.'),
    (os.path.join(vlc_path, 'libvlccore.dll'), '.'),
]

# Add VLC plugins
vlc_data = []
for root, dirs, files in os.walk(os.path.join(vlc_path, 'plugins')):
    for file in files:
        if file.endswith('.dll'):
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(os.path.dirname(full_path), vlc_path)
            vlc_data.append((full_path, rel_path))

a = Analysis(
    ['TT/main.py'],
    pathex=['c:\\Users\\Noah\\OneDrive\\Documents\\TT'],
    binaries=vlc_binaries,  # Add VLC binaries here
    datas=[
        ('TT/chat.wav', 'TT'),
        ('TT/directed.wav', 'TT'),
        ('TT/chat.wav', '_internal'),
        ('TT/directed.wav', '_internal'),
        ('TT/init_config.py', 'TT'),
        ('TT/ASCII_EXT.py', 'TT'),
        ('TT/image_patch.py', 'TT'),
    ] + vlc_data,  # Add VLC plugin data here
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