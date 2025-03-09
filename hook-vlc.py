from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files, copy_metadata

# Collect all VLC-related files
datas, binaries, hiddenimports = [], [], ['vlc']

# Add metadata for python-vlc
datas += copy_metadata('python-vlc')

# Make sure all requests-related modules are included for URL handling
hiddenimports.extend([
    'requests', 'urllib3', 'certifi', 'idna', 'chardet',
    'urllib3.contrib', 'urllib3.contrib.socks',
])