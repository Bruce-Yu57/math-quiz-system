# 數學出場卷系統 - 智能手寫辨識與 AI 批改

## 系統概述

這是一個專為數學課堂設計的智能出場卷系統，支援老師上傳數學題目圖片，AI 自動生成參考解答，學生透過手寫作答並獲得即時 AI 批改回饋。系統採用最新的 GPT-4o 技術進行手寫數學式辨識，能準確識別數學公式和繁體中文解題用詞。

## 🚀 核心特色

- **GPT-4o 手寫辨識**：使用最新的 GPT-4o 模型進行手寫數學式辨識
- **繁體中文支援**：完整支援「假設」、「因為」、「所以」等解題用詞
- **即時 AI 批改**：提供詳細的解題邏輯分析和回饋
- **響應式設計**：支援桌面和行動裝置
- **座號管理**：學生座號只在第一題輸入，自動套用到所有題目
- **答案自動載入**：切換題目時自動載入上次作答內容

## 🛠️ 技術架構

### 後端技術棧
- **Flask**: Python Web 框架，提供 RESTful API
- **SQLAlchemy**: ORM 資料庫操作
- **SQLite/PostgreSQL**: 資料庫支援
- **OpenAI GPT-4o**: AI 內容生成、批改與手寫辨識
- **Werkzeug**: 檔案上傳處理

### 前端技術棧
- **HTML5 + CSS3**: 響應式網頁設計
- **JavaScript (ES6+)**: 動態互動功能
- **Canvas API**: 手寫輸入處理
- **MathJax**: LaTeX 數學公式渲染
- **QRCode.js**: QR 碼生成

## 📋 環境設定

### 1. 建立 .env 檔案
在專案根目錄建立 `.env` 檔案：

```bash
# OpenAI API 設定（必需）
OPENAI_API_KEY=your_openai_api_key_here

# 資料庫設定（可選，預設使用 SQLite）
# DATABASE_URL=postgresql://username:password@localhost/dbname

# 伺服器設定（可選）
# PORT=10000
```

### 2. 取得 OpenAI API Key
1. 前往 [OpenAI Platform](https://platform.openai.com/api-keys)
2. 登入並建立新的 API Key
3. 複製金鑰並貼到 `.env` 檔案的 `OPENAI_API_KEY` 欄位

### 3. 安裝依賴套件
```bash
# 建立虛擬環境
python -m venv venv

# 啟動虛擬環境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安裝套件
pip install -r requirements.txt
```

## 🎯 功能模組

### 老師端功能

#### 1. 題目上傳與管理
- **多種上傳方式**：拖拽、點擊、Ctrl+V
- **檔案格式支援**：PNG, JPG, JPEG, GIF, BMP, TIFF
- **檔案大小限制**：16MB
- **即時預覽**：上傳後立即顯示題目內容

#### 2. AI 參考解答生成
- **GPT-4o 辨識**：自動辨識印刷題目內容
- **智能解答生成**：根據題目生成詳細解題步驟
- **LaTeX 格式**：支援數學公式排版
- **即時預覽**：老師可立即查看 AI 生成的解答

#### 3. 題組管理
- **QR 碼生成**：自動生成學生連結 QR 碼
- **連結分享**：提供學生端直接連結
- **題組重置**：可重新開始新的題組
- **管理員介面**：查看所有題組和學生作答

### 學生端功能

#### 1. 手寫輸入系統
- **Canvas 繪圖**：支援滑鼠和觸控輸入
- **畫筆/橡皮擦**：可切換繪圖模式
- **撤銷功能**：支援回到上一步
- **自動調整**：畫布大小根據螢幕自動調整

#### 2. GPT-4o 手寫辨識
- **數學公式辨識**：準確識別手寫數學符號和公式
- **繁體中文支援**：完整支援解題用詞如：
  - 邏輯連接詞：「或」、「且」、「若」、「則」
  - 解題步驟詞：「假設」、「令」、「因為」、「所以」、「故」
  - 運算過程詞：「得」、「代入」、「移項」、「化簡」
- **LaTeX 格式輸出**：自動轉換為標準數學格式
- **完整解題過程**：保留所有解題邏輯和說明

#### 3. AI 批改系統
- **邏輯分析**：分析學生解題過程的數學邏輯
- **寬鬆評分**：重點在於解題思路而非格式
- **詳細回饋**：明確指出錯誤步驟並提供正確解法
- **鼓勵性回覆**：以家教老師角度給予正面回饋

#### 4. 座號管理
- **一次輸入**：座號只在第一題輸入
- **自動套用**：後續題目自動使用相同座號
- **答案追蹤**：可查看所有題目的作答記錄

#### 5. 答案自動載入
- **切換題目**：自動載入上次作答內容
- **繼續編輯**：學生可繼續修改之前的答案
- **歷史記錄**：保留所有提交的答案版本

## 🗄️ 資料庫設計

### 資料表結構
```python
class QuizSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), unique=True, nullable=False)
    teacher = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), db.ForeignKey('quiz_set.session_id'))
    idx = db.Column(db.Integer, nullable=False)
    image_path = db.Column(db.String(256), nullable=True)
    image_blob = db.Column(db.LargeBinary)  # 圖片二進位資料
    ocr_text = db.Column(db.Text)  # 題目辨識文字
    ai_answer = db.Column(db.Text)  # AI 參考解答

class StudentAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    student_code = db.Column(db.String(64))  # 學生座號
    image_path = db.Column(db.String(256))  # 手寫答案圖片
    ocr_text = db.Column(db.Text)  # 手寫辨識結果
    ai_feedback = db.Column(db.Text)  # AI 批改回饋
    created_at = db.Column(db.DateTime, nullable=False)
```

## 🔌 API 端點

### 老師端 API
```
POST /api/upload_questions     # 上傳題目圖片
POST /api/reset               # 重置題組
GET  /api/all_quizsets        # 取得所有題組
POST /api/delete_session      # 刪除題組
GET  /api/image/<question_id> # 取得題目圖片
```

### 學生端 API
```
GET  /api/get_questions       # 取得題目列表
POST /api/upload_answer       # 上傳手寫答案
GET  /api/get_student_answers # 取得學生作答記錄
GET  /api/get_student_last_answer # 取得學生最後作答
```

## 🚀 快速開始

### 1. 啟動伺服器
```bash
# 啟動虛擬環境
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# 啟動伺服器
python main.py
```

### 2. 使用流程
1. **老師端**：開啟 `http://localhost:10000`
2. **上傳題目**：拖拽或點擊上傳數學題目圖片
3. **生成解答**：系統自動生成 AI 參考解答
4. **分享連結**：複製學生連結或 QR 碼
5. **學生作答**：學生開啟連結，輸入座號並手寫作答
6. **即時批改**：系統自動辨識並提供 AI 批改回饋

## 📱 使用範例

### 老師端操作
1. 上傳數學題目圖片
2. 系統自動辨識題目內容
3. AI 生成詳細參考解答
4. 生成學生連結和 QR 碼
5. 分享給學生

### 學生端操作
1. 開啟老師提供的連結
2. 在第一題輸入座號
3. 在畫布上手寫答案（包含中文解題用詞）
4. 點擊「送出」按鈕
5. 查看 AI 辨識結果和批改回饋

### 手寫辨識範例
**學生手寫內容：**
```
假設 x = 2
代入原式：x² + 3x + 1
= 2² + 3×2 + 1
= 4 + 6 + 1
= 11
```

**GPT-4o 辨識結果：**
```
假設 x = 2
代入原式：$x^2 + 3x + 1$
= $2^2 + 3 \times 2 + 1$
= $4 + 6 + 1$
= $11$
```

## 🔧 進階設定

### 自訂環境變數
```bash
# 開發環境
FLASK_ENV=development
DEBUG=True

# 生產環境
FLASK_ENV=production
DEBUG=False
```

### 資料庫設定
```bash
# SQLite（預設）
DATABASE_URL=sqlite:///math_quiz.db

# PostgreSQL
DATABASE_URL=postgresql://username:password@localhost/math_quiz
```

## 🐛 故障排除

### 常見問題
1. **OpenAI API 錯誤**：檢查 `.env` 檔案中的 API Key 是否正確
2. **圖片上傳失敗**：確認圖片格式和大小符合要求
3. **手寫辨識不準確**：確保手寫字跡清晰，包含完整解題過程
4. **伺服器無法啟動**：確認虛擬環境已啟動且套件已安裝

### 日誌查看
```bash
# 查看伺服器日誌
python main.py

# 查看錯誤訊息
# 檢查終端機輸出的錯誤資訊
```

## 📄 授權條款

本專案採用 MIT 授權條款，詳見 LICENSE 檔案。

## 🤝 貢獻指南

歡迎提交 Issue 和 Pull Request 來改善這個專案。

## 📞 聯絡資訊

如有問題或建議，請透過以下方式聯絡：
- 提交 GitHub Issue
- 發送 Email

---

**版本**：2.0.0  
**最後更新**：2024年6月  
**支援**：Python 3.8+, Flask 2.3+, OpenAI API 