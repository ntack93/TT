import os
import pathlib

def create_project_structure():
    # Get the current directory (TT folder)
    base_dir = pathlib.Path(__file__).parent

    # Define the directory structure
    directories = [
        'src',
        'src/ui',
        'src/network',
        'src/storage',
        'src/utils'
    ]

    # Create directories
    for dir_path in directories:
        full_path = base_dir / dir_path
        full_path.mkdir(exist_ok=True)
        # Create __init__.py in each directory
        (full_path / '__init__.py').touch()

    print("Created directory structure:")
    for dir_path in directories:
        print(f"✓ {dir_path}")

if __name__ == "__main__":
    create_project_structure()