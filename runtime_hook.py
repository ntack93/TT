"""
Runtime hook for PyInstaller to ensure PIL modules are available globally
and configure VLC paths
"""
import sys
import os

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

# Set up VLC environment
def setup_vlc():
    try:
        # Get the base directory (executable location in frozen app)
        base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        
        # Set VLC plugin path to our bundled plugins
        plugin_path = os.path.join(base_dir, 'plugins')
        if os.path.exists(plugin_path):
            os.environ['VLC_PLUGIN_PATH'] = plugin_path
            print(f"Runtime hook: VLC plugin path set to {plugin_path}")
        
        # Silence VLC messages
        os.environ['VLC_VERBOSE'] = '-1'
        
        # Force VLC to run in the correct mode
        os.environ['VLC_PLUGIN_PATH'] = plugin_path
        
        print("Runtime hook: VLC environment configured")
    except Exception as e:
        print(f"Runtime hook VLC configuration error: {e}")
        
# Call the setup function
setup_vlc()