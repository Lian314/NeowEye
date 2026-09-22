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
        "-y",  # Overwrite output directory without asking
        "--onedir",
        "--windowed",  # No black console window behind the game
        "--add-data=EO;EO",
        "--add-data=models;models",
        "--add-data=spire_mods;spire_mods",
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

    bind_bat_content = (
        "@echo off\r\n"
        "title NeowEye - 杀戮尖塔一键自动绑定工具\r\n"
        "cls\r\n"
        "echo ======================================================================\r\n"
        "echo           NeowEye 杀戮尖塔 AI 战术助手 - 一键自动绑定\r\n"
        "echo ======================================================================\r\n"
        "echo.\r\n"
        "echo 正在自动检测当前路径并配置 CommunicationMod...\r\n"
        "echo.\r\n"
        "set \"NEOWEYE_EXE=%~dp0NeowEye.exe\"\r\n"
        "set \"SAFE_EXE=%NEOWEYE_EXE:\\=/%\"\r\n"
        "set \"CONFIG_DIR=%LOCALAPPDATA%\\ModTheSpire\\CommunicationMod\"\r\n"
        "if not exist \"%CONFIG_DIR%\" (\r\n"
        "    mkdir \"%CONFIG_DIR%\" 2>nul\r\n"
        ")\r\n"
        "set \"CONFIG_FILE=%CONFIG_DIR%\\config.properties\"\r\n"
        "> \"%CONFIG_FILE%\" echo command=\"%SAFE_EXE%\" --mode stdin\r\n"
        ">> \"%CONFIG_FILE%\" echo runAtGameStart=true\r\n"
        ">> \"%CONFIG_FILE%\" echo verbose=false\r\n"
        "if exist \"%CONFIG_FILE%\" (\r\n"
        "    echo [OK] 绑定成功！已自动写入配置文件:\r\n"
        "    echo %CONFIG_FILE%\r\n"
        "    echo.\r\n"
        "    echo 写入内容:\r\n"
        "    type \"%CONFIG_FILE%\"\r\n"
        "    echo.\r\n"
        "    echo ======================================================================\r\n"
        "    echo 【使用说明】:\r\n"
        "    echo 1. 确保已在创意工坊订阅 ModTheSpire、BaseMod 与 CommunicationMod\r\n"
        "    echo 2. 打开 Steam 启动 杀戮尖塔，在弹出的启动选项中选择 Play with Mods\r\n"
        "    echo 3. 在 Mod 列表中勾选 CommunicationMod，点击 Play 即可\r\n"
        "    echo 4. NeowEye 战术悬浮窗将会在游戏进入后全自动呼出！\r\n"
        "    echo ======================================================================\r\n"
        ") else (\r\n"
        "    echo [错误] 配置文件写入失败，请以管理员身份运行此脚本！\r\n"
        ")\r\n"
        "pause\r\n"
    )
    with open(os.path.join(app_dist_dir, "一键自动绑定杀戮尖塔.bat"), "w", encoding="gbk") as f:
        f.write(bind_bat_content)
    with open(os.path.join(root_dir, "一键自动绑定杀戮尖塔.bat"), "w", encoding="gbk") as f:
        f.write(bind_bat_content)

    print(f"Build succeeded! Standalone executable is ready at: {app_dist_dir}\\NeowEye.exe")

    # 3. Create zip archive
    print("\n=== 3. Packaging into ZIP archive for release ===")
    zip_path = os.path.join(dist_dir, "NeowEye-v1.0.0-windows-x64")
    shutil.make_archive(zip_path, "zip", dist_dir, "NeowEye")
    print(f"Release ZIP created at: {zip_path}.zip ({os.path.getsize(zip_path + '.zip') / (1024*1024):.1f} MB)")
    return True

if __name__ == "__main__":
    build()
