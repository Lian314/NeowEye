@echo off
cd /d "%~dp0"
chcp 936 >nul
title 杀戮尖塔 实时战术辅助器

set "PYTHON_EXE=C:\Users\Admin\.local\bin\python3.12.exe"
if not exist "%PYTHON_EXE%" (
    where py >nul 2>nul && (set "PYTHON_EXE=py -3") || (set "PYTHON_EXE=python")
)

:MENU
cls
echo ================================================================
echo   杀戮尖塔 实时战术辅助器 (Slay the Spire Tactical Assistant)
echo   基于 Laya 决策模型 (421M 编码器) + 战斗手牌数学精算引擎
echo ================================================================
echo.
echo [1] 启动独立演示/悬浮测试模式 (Mock Mode - 直接启动置顶悬浮窗)
echo [2] 启动 CommunicationMod 联动模式 (Stdin Mode - 游戏内实时监听)
echo [3] 运行全量自动化测试 (Combat Solver / Laya API / Macro Advisor)
echo [0] 退出
echo.

set "choice="
set /p choice="请选择运行模式 [回车默认 1]: "
if "%choice%"=="" set choice=1

if "%choice%"=="1" goto MOCK
if "%choice%"=="2" goto STDIN
if "%choice%"=="3" goto TEST
if "%choice%"=="0" goto EXIT
goto MOCK

:MOCK
echo.
echo 正在启动置顶透明悬浮窗 (Mock 测试模式)...
"%PYTHON_EXE%" main.py --mode mock
goto END

:STDIN
echo.
echo 正在启动 CommunicationMod 游戏监听模式...
"%PYTHON_EXE%" main.py --mode stdin
goto END

:TEST
echo.
echo 正在执行自动化测试 (共 10 项测试用例)...
echo ----------------------------------------------------------------
"%PYTHON_EXE%" -m unittest discover tests
echo ----------------------------------------------------------------
goto END

:END
echo.
echo ================================================================
echo   执行完成！按任意键返回菜单...
echo ================================================================
pause
goto MENU

:EXIT
exit /b 0
