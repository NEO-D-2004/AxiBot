import os
import shutil
import sys
import subprocess
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

        # 3. Compile Inno Setup Installer if Inno Setup is installed
        print("\n=== Compiling Standalone Setup Installer ===")
        
        # Try to locate ISCC.exe in PATH, or check default installation directories
        iscc_path = shutil.which("iscc")
        if not iscc_path:
            common_paths = [
                r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
                r"C:\Program Files\Inno Setup 6\ISCC.exe",
                os.path.expandvars(r"%LocalAppData%\Programs\Inno Setup 6\ISCC.exe")
            ]
            for p in common_paths:
                if os.path.exists(p):
                    iscc_path = p
                    break
        
        if iscc_path:
            print(f"Found Inno Setup Compiler (ISCC) at: {iscc_path}")
            iss_script = "installer.iss"
            if os.path.exists(iss_script):
                print(f"Running Inno Setup compilation for {iss_script}...")
                try:
                    subprocess.run([iscc_path, iss_script], check=True)
                    print("\n=== Setup Installer Compiled Successfully ===")
                    print(f"Setup installer location: {os.path.abspath('dist-installer/AxiBotSetup.exe')}")
                except subprocess.CalledProcessError as err:
                    print(f"Error: Inno Setup compilation failed with exit code {err.returncode}")
            else:
                print(f"Error: Inno Setup script '{iss_script}' not found in root.")
        else:
            print("Inno Setup (ISCC.exe) not found in PATH or standard Program Files locations.")
            print("Please ensure Inno Setup is installed to automatically compile the installer.")
    except Exception as e:
        print(f"Build failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
