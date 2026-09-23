@echo off
chcp 65001 >nul
pushd "%~dp0"

echo ======================================
echo   节气药膳师 · 专业版 正在启动...
echo ======================================
echo.

REM ---------- 1. 检查并自动安装依赖 ----------
python -c "import fastapi, uvicorn, sqlalchemy, pydantic" >nul 2>&1
if errorlevel 1 (
    echo [1/3] 首次运行，正在安装依赖，请稍候...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo        官方源超时，改试阿里云镜像...
        python -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
    )
    if errorlevel 1 (
        echo.
        echo [失败] 依赖安装出错，请检查 Python 与网络后重试。
        echo       也可手动执行： pip install -r requirements.txt
        popd
        pause
        exit /b 1
    )
) else (
    echo [1/3] 依赖已就绪，跳过安装。
)

REM ---------- 2. 初始化数据库 ----------
echo [2/3] 正在初始化数据库...
pushd backend
python init_db.py
if errorlevel 1 (
    echo.
    echo [失败] 数据库初始化出错，请看上方报错信息。
    popd
    popd
    pause
    exit /b 1
)

REM ---------- 3. 启动服务 ----------
netstat -ano | findstr ":8000" | findstr "LISTENING" >nul
if not errorlevel 1 (
    echo [提示] 8000 端口已被占用，服务多半已经在运行。
    echo        直接访问 http://127.0.0.1:8000
    echo        若页面报"连不上后端"，先关掉旧的黑窗口再重新运行本脚本。
    echo.
    start http://127.0.0.1:8000
    popd
    popd
    pause
    exit /b 0
)

echo.
echo [3/3] 服务启动中...
echo ======================================
echo   浏览器访问: http://127.0.0.1:8000
echo   停止服务请按 Ctrl+C
echo   !! 关掉本窗口 = 停服务，菜单会生成失败 !!
echo ======================================
echo.
start "" cmd /c "ping -n 5 127.0.0.1 >nul & start http://127.0.0.1:8000"
python -m uvicorn main:app --host 127.0.0.1 --port 8000

popd
popd
pause
