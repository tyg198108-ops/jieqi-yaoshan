@echo off
chcp 65001 >nul
title 节气药膳师 · 部署到腾讯云开发

echo ==========================================
echo   节气药膳师 · 一键部署到腾讯云开发
echo ==========================================
echo.
echo 会按顺序做三件事：
echo   1. 构建产物到 dist/
echo   2. 部署后端云函数 yaoshan-api
echo   3. 部署前端静态站 dist/web
echo.
echo 中途会弹出浏览器要求登录腾讯云，登录完回到这个窗口即可。
echo.
pause

set PY=%~dp0
cd /d "%PY%"

echo.
echo ---------- [1/3] 构建产物 ----------
python _build_cloud.py
if errorlevel 1 (
  echo.
  echo [出错] 构建失败。请确认已安装 Python 并把 python 加入环境变量 PATH。
  goto :end
)

echo.
echo ---------- [2/3] 部署后端云函数 ----------
call npx --yes @cloudbase/cli@latest fn deploy yaoshan-api -e jieqi-yaoshan-d7gd6ypfscd10299f --force
if errorlevel 1 (
  echo.
  echo [出错] 云函数部署失败。
  echo 常见原因：未登录（弹出浏览器后需要登录）、环境 ID 不对、云函数包路径不对。
  goto :end
)

echo.
echo ---------- [3/3] 部署前端静态站 ----------
call npx --yes @cloudbase/cli@latest hosting deploy dist/web -e jieqi-yaoshan-d7gd6ypfscd10299f --force
if errorlevel 1 (
  echo.
  echo [出错] 静态站部署失败。
  goto :end
)

echo.
echo ==========================================
echo   部署完成
echo ==========================================
echo.
echo 还剩两件事必须做，否则线上只有前端、没有后端：
echo.
echo   1. 控制台 → HTTP 访问服务 → 新建，路径填 /api/* 关联云函数 yaoshan-api
echo      拿到形如 https://xxx.service.tcloudbase.com 的域名后，
echo      把它填进 js/cloud-config.js 的 apiBase，再跑一次本脚本。
echo.
echo   2. 控制台 → 静态网站托管 → 域名管理，查看免费默认域名
echo      （形如 https://xxx.tcloudbaseapp.com），这就是发给用户的网址。
echo.
echo 详细图文步骤见：部署上线手册.md

:end
echo.
pause
