@echo off
echo 手寫數學式辨識系統啟動中...
echo.
echo 請確保已安裝 Python 3.11 和所需套件
echo.
python --version
echo.
echo 正在啟動 Flask 應用程式...
echo 網頁將在 http://localhost:5000 開啟
echo 按 Ctrl+C 停止服務器
echo.
py -3.11 app.py
pause 