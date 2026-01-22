#!/usr/bin/env python3
"""
AI Manager v11.0 - Windows Build Script
Builds executable for Windows using PyInstaller

Usage:
    python build_windows.py           # Build standard exe
    python build_windows.py --onedir  # Build directory-based exe (faster startup)
    python build_windows.py --debug   # Build with console for debugging
    python build_windows.py --installer  # Create Inno Setup script
    python build_windows.py --clean   # Clean build artifacts only
"""

import os
import sys
import subprocess
import shutil
import glob
from pathlib import Path


def check_dependencies():
    """Check if required packages are installed"""
    missing = []

    try:
        import customtkinter
    except ImportError:
        missing.append("customtkinter")

    try:
        import requests
    except ImportError:
        missing.append("requests")

    try:
        import PyInstaller
    except ImportError:
        missing.append("pyinstaller")

    if missing:
        print(f"Missing packages: {', '.join(missing)}")
        print("Installing missing packages...")
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
        print("Packages installed successfully!")

    return True


def clean_build():
    """Clean previous build artifacts"""
    dirs_to_clean = ["build", "dist", "__pycache__"]

    for d in dirs_to_clean:
        if os.path.exists(d):
            print(f"Cleaning {d}/...")
            try:
                shutil.rmtree(d)
            except PermissionError as e:
                print(f"WARNING: Cannot delete {d}/ - file may be in use")
                print(f"  Error: {e}")
                print(f"  Please close AI_Manager.exe if it's running")
                if "dist" in d:
                    response = input("Continue anyway? (y/n): ").strip().lower()
                    if response != 'y':
                        print("Build aborted.")
                        sys.exit(1)

    for f in glob.glob("*.spec"):
        print(f"Removing {f}...")
        try:
            os.remove(f)
        except PermissionError:
            print(f"WARNING: Cannot delete {f}")


def get_customtkinter_path():
    """Get the path to customtkinter package"""
    try:
        import customtkinter
        return os.path.dirname(customtkinter.__file__)
    except ImportError:
        return None


def build_exe(onefile=True, debug=False):
    """Build the Windows executable"""

    # Determine main script
    main_script = "main.py"
    if not os.path.exists(main_script):
        print(f"Error: {main_script} not found!")
        return False

    # Build PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "AI_Manager",
        "--clean",
        "--noconfirm",
    ]

    # One file or one directory
    if onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")

    # Console or windowed
    if debug:
        cmd.append("--console")
        print("Building with console (debug mode)...")
    else:
        cmd.append("--windowed")
        print("Building windowed application...")

    # Add customtkinter data
    cmd.extend(["--collect-all", "customtkinter"])

    # Add icon if exists
    for icon_path in ["icon.ico", "assets/icon.ico"]:
        if os.path.exists(icon_path):
            cmd.extend(["--icon", icon_path])
            print(f"Using icon: {icon_path}")
            break

    # Add ai_manager package
    if os.path.exists("ai_manager"):
        cmd.extend(["--add-data", f"ai_manager{os.pathsep}ai_manager"])

    # Hidden imports
    hidden_imports = [
        "customtkinter",
        "requests",
        "json",
        "threading",
        "queue",
    ]

    # Optional hidden imports
    try:
        import keyring
        hidden_imports.append("keyring")
        hidden_imports.append("keyring.backends")
    except ImportError:
        pass

    try:
        import tiktoken
        hidden_imports.append("tiktoken")
        hidden_imports.append("tiktoken_ext")
        hidden_imports.append("tiktoken_ext.openai_public")
    except ImportError:
        pass

    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    # Add main script
    cmd.append(main_script)

    print("Running PyInstaller...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 50)

    try:
        subprocess.check_call(cmd)
        print("-" * 50)
        print("Build completed successfully!")

        if onefile:
            exe_path = os.path.join("dist", "AI_Manager.exe")
        else:
            exe_path = os.path.join("dist", "AI_Manager", "AI_Manager.exe")

        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"Executable: {exe_path}")
            print(f"Size: {size_mb:.1f} MB")

        return True

    except subprocess.CalledProcessError as e:
        print(f"Build failed with error: {e}")
        return False


def create_installer_script():
    """Create Inno Setup installer script"""

    inno_script = '''; AI Manager - Inno Setup Installer Script
; Compile with Inno Setup 6.x (https://jrsoftware.org/isinfo.php)

#define MyAppName "AI Manager"
#define MyAppVersion "11.0"
#define MyAppPublisher "AI Manager"
#define MyAppExeName "AI_Manager.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=installer
OutputBaseFilename=AI_Manager_Setup_v{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; For --onefile build:
Source: "dist\\AI_Manager.exe"; DestDir: "{app}"; Flags: ignoreversion

; For --onedir build (uncomment below, comment above):
; Source: "dist\\AI_Manager\\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"
Name: "{group}\\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
'''

    with open("installer.iss", "w", encoding="utf-8") as f:
        f.write(inno_script)

    print("Created installer.iss (Inno Setup script)")
    print("\nTo create installer:")
    print("  1. Download Inno Setup: https://jrsoftware.org/isinfo.php")
    print("  2. Install Inno Setup")
    print("  3. Open installer.iss in Inno Setup Compiler")
    print("  4. Click Build > Compile")
    print("  5. Installer will be in 'installer/' folder")


def main():
    """Main build function"""
    print("=" * 50)
    print("AI Manager v11.0 - Windows Build Script")
    print("=" * 50)

    # Check Python version
    if sys.version_info < (3, 8):
        print("ERROR: Python 3.8+ required")
        sys.exit(1)

    print(f"Python version: {sys.version}")
    print()

    # Parse arguments
    onefile = "--onedir" not in sys.argv
    debug = "--debug" in sys.argv
    create_installer = "--installer" in sys.argv
    clean_only = "--clean" in sys.argv

    # Change to script directory
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)

    # Clean previous build
    clean_build()

    if clean_only:
        print("Clean completed.")
        return

    # Check dependencies
    print("\nChecking dependencies...")
    if not check_dependencies():
        return

    # Build executable
    print("\nBuilding executable...")
    if not build_exe(onefile=onefile, debug=debug):
        return

    # Create installer script if requested
    if create_installer:
        print("\nCreating installer script...")
        create_installer_script()

    print("\n" + "=" * 50)
    print("BUILD COMPLETE!")
    print("=" * 50)
    print("\nUsage options:")
    print("  --onedir     Build as directory (faster startup)")
    print("  --debug      Build with console window")
    print("  --installer  Create Inno Setup script")
    print("  --clean      Clean build artifacts only")


if __name__ == "__main__":
    main()
