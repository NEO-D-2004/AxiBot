import os
import shutil
import sys
import PyInstaller.__main__

def main():
    print("=== Starting AxiBot Desktop Build Process ===")
    
    # 1. Clean previous build folders
    folders_to_clean = ["build", "dist"]
    for folder in folders_to_clean:
        if os.path.exists(folder):
            print(f"Cleaning existing directory: {folder}...")
            try:
                shutil.rmtree(folder)
            except Exception as e:
                print(f"Warning: Could not remove {folder}: {e}")

    # 2. Configure PyInstaller arguments
    # On Windows, add-data separator must be a semicolon (;)
    ui_data_param = "app/ui;app/ui"
    
    args = [
        'main_gui.py',
        '--name=AxiBot',
        '--onedir',          # Produce a folder containing executable and DLLs (highly recommended for PyWebView stability)
        '--windowed',         # No console window
        '--icon=app/ui/app-logo.ico',
        f'--add-data={ui_data_param}',
        '--noconfirm',
        '--clean'
    ]
    
    print(f"Running PyInstaller with arguments: {args}")
    
    try:
        PyInstaller.__main__.run(args)
        
        # Copy configuration files if they exist in root
        target_dir = os.path.join("dist", "AxiBot")
        if os.path.exists("client_secret.json"):
            shutil.copy("client_secret.json", target_dir)
            print("Copied client_secret.json into dist/AxiBot/")
        if os.path.exists(".env"):
            shutil.copy(".env", target_dir)
            print("Copied .env into dist/AxiBot/")

        print("\n=== Build Complete ===")
        print("Your AxiBot desktop application is ready!")
        print(f"Executable location: {os.path.abspath('dist/AxiBot/AxiBot.exe')}")
        print("\nNote: Make sure your '.env' and 'client_secret.json' files are in the same folder as 'AxiBot.exe' when distributing.")
    except Exception as e:
        print(f"Build failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
