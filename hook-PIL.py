from PyInstaller.utils.hooks import collect_all, collect_submodules

# Get everything related to PIL
datas, binaries, hiddenimports = collect_all('PIL')

# Add explicit imports of common PIL modules
hiddenimports += [
    'PIL',
    'PIL.Image', 
    'PIL.ImageTk',
    'PIL._imaging',
    'PIL.ImageFile',
    'PIL._tkinter_finder',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'PIL.ImageFilter',
    'PIL.ImageOps',
    'PIL.ImageEnhance',
    'PIL.BmpImagePlugin',
    'PIL.GifImagePlugin',
    'PIL.JpegImagePlugin',
    'PIL.PngImagePlugin',
]

# Try to get Pillow metadata (not PIL)
try:
    from PyInstaller.utils.hooks import copy_metadata
    datas += copy_metadata('Pillow')
except Exception as e:
    print(f"Warning: Could not copy Pillow metadata: {e}")