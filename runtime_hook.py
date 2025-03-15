"""
Runtime hook for PyInstaller to ensure PIL modules are available globally
and configure VLC paths
"""
import os
import sys
import traceback

# Ensure PIL can be found
if hasattr(sys, '_MEIPASS'):
    # Add paths to search for PIL
    sys.path.insert(0, sys._MEIPASS)
    
    # Explicitly set DLL search paths for PIL dependencies
    os.environ['PATH'] = sys._MEIPASS + os.pathsep + os.environ['PATH']

# Adjust Python path to find packaged VLC
if hasattr(sys, '_MEIPASS'):
    # Running as PyInstaller bundle
    os.environ['PYTHONPATH'] = sys._MEIPASS
    os.environ['VLC_PLUGIN_PATH'] = os.path.join(sys._MEIPASS, 'vlc', 'plugins')

# Ensure PIL modules are available globally
try:
    import PIL.Image
    import PIL.ImageTk
    
    # Add to global namespace
    sys.modules['Image'] = PIL.Image
    sys.modules['ImageTk'] = PIL.ImageTk
    
    print("PIL modules made globally available")
except Exception as e:
    print(f"Error importing PIL: {e}")

# Setup VLC environment variables for packaged application
def setup_vlc():
    try:
        print("Setting up VLC environment...")
        
        # Get the base directory
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            base_dir = os.path.dirname(sys.executable)
        else:
            # Running in development mode
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
        print(f"Base directory: {base_dir}")
        
        # Make sure VLC can find its DLLs
        os.environ['PATH'] = base_dir + os.pathsep + os.environ['PATH']
        
        # Set plugin path
        plugin_path = os.path.join(base_dir, 'plugins')
        if os.path.exists(plugin_path):
            os.environ['VLC_PLUGIN_PATH'] = plugin_path
            print(f"Set VLC_PLUGIN_PATH to {plugin_path}")
        else:
            print(f"Warning: VLC plugin path not found: {plugin_path}")
            
        # Silence VLC messages
        os.environ['VLC_VERBOSE'] = '-1'
            
    except Exception as e:
        print(f"Error setting up VLC environment: {e}")
        traceback.print_exc()

# Call setup function
setup_vlc()