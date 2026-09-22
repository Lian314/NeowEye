@echo off
title NeowEye - 杀戮尖塔一键自动绑定工具
cls
echo ======================================================================
echo           NeowEye 杀戮尖塔 AI 战术助手 - 一键自动绑定
echo ======================================================================
echo.
echo 正在自动检测当前路径并配置 CommunicationMod...
echo.
set "NEOWEYE_EXE=%~dp0NeowEye.exe"
set "SAFE_EXE=%NEOWEYE_EXE:\=/%"
set "CONFIG_DIR=%LOCALAPPDATA%\ModTheSpire\CommunicationMod"
if not exist "%CONFIG_DIR%" (
    mkdir "%CONFIG_DIR%" 2>nul
)
set "CONFIG_FILE=%CONFIG_DIR%\config.properties"
> "%CONFIG_FILE%" echo command="%SAFE_EXE%" --mode stdin
>> "%CONFIG_FILE%" echo runAtGameStart=true
>> "%CONFIG_FILE%" echo verbose=false
if exist "%CONFIG_FILE%" (
    echo [OK] 绑定成功！已自动写入配置文件:
    echo %CONFIG_FILE%
    echo.
    echo 写入内容:
    type "%CONFIG_FILE%"
    echo.
    echo ======================================================================
    echo 【使用说明】:
    echo 1. 确保已在创意工坊订阅 ModTheSpire、BaseMod 与 CommunicationMod
    echo 2. 打开 Steam 启动 杀戮尖塔，在弹出的启动选项中选择 Play with Mods
    echo 3. 在 Mod 列表中勾选 CommunicationMod，点击 Play 即可
    echo 4. NeowEye 战术悬浮窗将会在游戏进入后全自动呼出！
    echo ======================================================================
) else (
    echo [错误] 配置文件写入失败，请以管理员身份运行此脚本！
)
pause
