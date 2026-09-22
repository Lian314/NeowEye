"""
NeowEye Standalone Packaging Script using PyInstaller.
Bundles:
1. Python Runtime + Compiled Bytecode
2. ONNX Runtime DLLs & Execution Providers
3. Tokenizers Rust binaries
4. EO Database (cards, relics, monsters, powers)
5. Models Directory (laya_int8.onnx, tokenizer.json)
Produces a clean, standalone green folder in dist/NeowEye/
"""
import os
import sys
import shutil
import subprocess

def build():
    print("=== 1. Starting NeowEye Standalone Build with PyInstaller ===")
    root_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(root_dir, "dist")
    build_dir = os.path.join(root_dir, "build")

    # Clean previous build artifacts
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir, ignore_errors=True)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=NeowEye",
        "--onedir",
        "--windowed",  # No black console window behind the game
        "--add-data=EO;EO",
        "--add-data=models;models",
        "--hidden-import=onnxruntime",
        "--hidden-import=tokenizers",
        "--hidden-import=numpy",
        "--hidden-import=tkinter",
        "--hidden-import=ctypes",
        os.path.join(root_dir, "main.py")
    ]

    print("Running command:", " ".join(cmd))
    res = subprocess.run(cmd, cwd=root_dir)
    if res.returncode != 0:
        print(f"PyInstaller build failed with exit code {res.returncode}")
        return False

    print("\n=== 2. Creating Quick Launchers in dist/NeowEye ===")
    app_dist_dir = os.path.join(dist_dir, "NeowEye")

    # Create convenient launcher bat in dist/NeowEye
    bat_content = (
        "@echo off\r\n"
        "cd /d \"%~dp0\"\r\n"
        "title NeowEye - 杀戮尖塔 AI 战术辅助器\r\n"
        "start \"\" \"NeowEye.exe\" --mode mock\r\n"
    )
    with open(os.path.join(app_dist_dir, "启动NeowEye(演示模式).bat"), "w", encoding="gbk") as f:
        f.write(bat_content)

    print(f"Build succeeded! Standalone executable is ready at: {app_dist_dir}\\NeowEye.exe")

    # 3. Create zip archive
    print("\n=== 3. Packaging into ZIP archive for release ===")
    zip_path = os.path.join(dist_dir, "NeowEye-v1.0.0-windows-x64")
    shutil.make_archive(zip_path, "zip", dist_dir, "NeowEye")
    print(f"Release ZIP created at: {zip_path}.zip ({os.path.getsize(zip_path + '.zip') / (1024*1024):.1f} MB)")
    return True

if __name__ == "__main__":
    build()
