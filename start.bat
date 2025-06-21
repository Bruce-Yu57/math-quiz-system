@echo off
echo 設定 Flask 應用程式指向 main.py...
set FLASK_APP=main.py
set FLASK_ENV=development

echo.
echo 正在啟動 Flask 開發伺服器...
echo 您可以在 http://localhost:5000 訪問應用程式
echo 按下 Ctrl+C 來停止伺服器
echo.

flask run 