#!/usr/bin/env python3
"""
AI Manager - Cross-platform Build Script
Builds executable for Windows using PyInstaller
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def main():
    print("=" * 50)
    print("AI Manager - Build Script")
    print("=" * 50)
    print()

    # Check Python version
    if sys.version_info < (3, 8):
        print("ERROR: Python 3.8+ required")
        sys.exit(1)

    print(f"Python version: {sys.version}")
    print()

    # Get script directory
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)

    # Step 1: Install dependencies
    print("[1/4] Installing dependencies...")
    subprocess.run([
        sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
    ], check=True)

    # Step 2: Install PyInstaller
    print()
    print("[2/4] Installing PyInstaller...")
    subprocess.run([
        sys.executable, "-m", "pip", "install", "pyinstaller"
    ], check=True)

    # Step 3: Build executable
    print()
    print("[3/4] Building executable...")

    # PyInstaller arguments
    args = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "AI_Manager",
        "--clean",
    ]

    # Add icon if exists
    icon_path = script_dir / "icon.ico"
    if icon_path.exists():
        args.extend(["--icon", str(icon_path)])
        print(f"  Using icon: {icon_path}")

    # Add main script
    args.append("main_app.py")

    # Run PyInstaller
    result = subprocess.run(args)

    if result.returncode != 0:
        print("ERROR: Build failed")
        sys.exit(1)

    # Step 4: Cleanup
    print()
    print("[4/4] Cleaning up...")

    # Remove build directory
    build_dir = script_dir / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)

    # Remove spec file
    spec_file = script_dir / "AI_Manager.spec"
    if spec_file.exists():
        spec_file.unlink()

    # Success message
    print()
    print("=" * 50)
    print("BUILD COMPLETE!")
    print("=" * 50)
    print()

    dist_dir = script_dir / "dist"
    if sys.platform == "win32":
        exe_path = dist_dir / "AI_Manager.exe"
    else:
        exe_path = dist_dir / "AI_Manager"

    print(f"Executable location: {exe_path}")
    print()

    if exe_path.exists():
        print(f"File size: {exe_path.stat().st_size / 1024 / 1024:.1f} MB")
    print()


if __name__ == "__main__":
    main()
