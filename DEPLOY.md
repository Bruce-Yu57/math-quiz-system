# Render 部署指南

## 部署前準備

### 1. 確保檔案已準備
- ✅ `requirements.txt` - Python依賴套件
- ✅ `Procfile` - Render啟動配置
- ✅ `runtime.txt` - Python版本指定
- ✅ `main.py` - 主應用程式（已支援Render）

### 2. 準備環境變數
在Render部署時需要設置以下環境變數：
- `OPENAI_API_KEY` - OpenAI API金鑰
- `DATABASE_URL` - 會由Render自動提供

## 部署步驟

### 步驟1：註冊Render帳號
1. 前往 [render.com](https://render.com)
2. 使用GitHub帳號註冊
3. 完成帳號驗證

### 步驟2：連接GitHub倉庫
1. 在Render Dashboard點擊 "New +"
2. 選擇 "Web Service"
3. 連接您的GitHub帳號
4. 選擇包含此專案的倉庫

### 步驟3：配置Web Service
1. **Name**: `math-quiz-system` (或您喜歡的名稱)
2. **Environment**: `Python 3`
3. **Build Command**: `pip install -r requirements.txt`
4. **Start Command**: `gunicorn main:app`
5. **Plan**: 選擇免費方案

### 步驟4：設置環境變數
在 "Environment" 標籤頁添加：
- **Key**: `OPENAI_API_KEY`
- **Value**: 您的OpenAI API金鑰

### 步驟5：部署
1. 點擊 "Create Web Service"
2. 等待部署完成（約5-10分鐘）
3. 部署成功後會顯示URL

## 部署後配置

### 1. 檢查部署狀態
- 在Render Dashboard查看部署日誌
- 確認沒有錯誤訊息
- 測試網站功能

### 2. 自定義域名（可選）
- 在 "Settings" 標籤頁
- 點擊 "Custom Domains"
- 添加您的域名

### 3. 監控和日誌
- 在 "Logs" 標籤頁查看應用程式日誌
- 監控效能和錯誤

## 常見問題

### Q1: 部署失敗怎麼辦？
**A**: 檢查以下項目：
- requirements.txt格式是否正確
- Python版本是否支援
- 環境變數是否正確設置

### Q2: 資料庫連接失敗？
**A**: 
- 確認DATABASE_URL環境變數存在
- 檢查PostgreSQL服務是否正常
- 查看應用程式日誌

### Q3: OpenAI API錯誤？
**A**:
- 確認OPENAI_API_KEY正確
- 檢查API配額是否足夠
- 確認網路連線正常

### Q4: 靜態檔案無法載入？
**A**:
- 確認uploads資料夾存在
- 檢查檔案權限
- 確認URL路徑正確

## 免費方案限制

### Render免費方案限制：
- **每月750小時**運行時間
- **512MB RAM**
- **共享CPU**
- **冷啟動較慢**

### 建議：
- 適合測試和小型使用
- 如需生產環境建議升級到付費方案

## 升級到付費方案

### 何時需要升級：
- 使用量超過免費限制
- 需要更好的效能
- 需要自定義域名
- 需要更多資源

### 升級步驟：
1. 在Render Dashboard選擇您的服務
2. 點擊 "Settings"
3. 選擇付費方案
4. 完成付款設置

## 備份和遷移

### 資料備份：
- 定期導出資料庫
- 備份上傳的圖片檔案
- 保存環境變數配置

### 遷移到其他平台：
- 修改資料庫配置
- 更新環境變數
- 調整部署配置

---

**部署完成後，您的數學出場卷系統就可以在網際網路上使用了！** 