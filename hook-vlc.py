from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files

# Collect all VLC-related files
datas, binaries, hiddenimports = [], [], ['vlc']

# Ensure VLC modules are included
try:
    import vlc
    if hasattr(vlc, '__file__'):  # Check if it's a real module
        hiddenimports.append('vlc')
except ImportError:
    pass

# Make sure all requests-related modules are included for URL handling
hiddenimports.extend([
    'requests', 'urllib3', 'certifi', 'idna', 'chardet',
    'urllib3.contrib', 'urllib3.contrib.socks',
])