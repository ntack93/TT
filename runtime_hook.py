"""
Runtime hook for PyInstaller to ensure PIL modules are available globally
"""
import sys

# Ensure PIL modules are available globally
try:
    import PIL.Image
    import PIL.ImageTk
    
    # Add to global namespace
    sys.modules['Image'] = PIL.Image
    sys.modules['ImageTk'] = PIL.ImageTk
    
    print("Runtime hook: PIL modules made globally available")
except Exception as e:
    print(f"Runtime hook error: {e}")