"""
Patch for PIL and requests to work better in PyInstaller
"""
import os
import sys
import tempfile
import traceback
from pathlib import Path

# Make PIL modules globally available
import PIL
import PIL.Image
import PIL.ImageTk

# Create global variables that can be imported
Image = PIL.Image
ImageTk = PIL.ImageTk

def setup_temp_dir():
    """
    Setup a writable temp directory for the application
    """
    if getattr(sys, 'frozen', False):
        # If running as bundled exe
        try:
            # Create a temp directory in AppData
            app_temp = os.path.join(
                os.environ.get('APPDATA', os.path.expanduser('~')),
                'TeleconferenceTerminal',
                'temp'
            )
            if not os.path.exists(app_temp):
                os.makedirs(app_temp)
            
            # Set environment variables to use this directory
            os.environ['TEMP'] = app_temp
            os.environ['TMP'] = app_temp
            tempfile.tempdir = app_temp
            
            print(f"Using custom temp directory: {app_temp}")
            return True
        except Exception as e:
            print(f"Error setting up temp directory: {e}")
            traceback.print_exc()
    return False

def patch_requests_session():
    """
    Patch the requests session to work better in PyInstaller
    """
    try:
        import requests
        from requests.adapters import HTTPAdapter
        
        # Create a custom session with longer timeouts
        original_session = requests.Session
        
        def patched_session():
            session = original_session()
            # Add retry adapter with backoff
            adapter = HTTPAdapter(max_retries=3)
            session.mount('http://', adapter)
            session.mount('https://', adapter)
            # Set longer timeout
            session.request = lambda method, url, **kwargs: \
                original_session.request(session, method, url, 
                                        timeout=kwargs.pop('timeout', 10), **kwargs)
            return session
        
        # Replace the session function
        requests.Session = patched_session
        return True
    except Exception as e:
        print(f"Error patching requests: {e}")
        traceback.print_exc()
        return False

def apply_patches():
    """Apply all patches"""
    success = []
    success.append(setup_temp_dir())
    success.append(patch_requests_session())
    
    print(f"Applied patches: {sum(success)}/{len(success)} successful")
    print(f"PIL modules available: Image={Image is not None}, ImageTk={ImageTk is not None}")
    
    # Ensure PIL modules are available in the global namespace
    # This helps with "name 'Image' is not defined" errors
    try:
        # Add to global namespace
        sys.modules['Image'] = PIL.Image
        sys.modules['ImageTk'] = PIL.ImageTk
        
        # Make globals accessible
        globals()['Image'] = PIL.Image
        globals()['ImageTk'] = PIL.ImageTk
    except Exception as e:
        print(f"Error setting PIL globals: {e}")
        traceback.print_exc()