# 數學出場卷系統 - 詳細技術說明書

## 系統概述

這是一個專為數學課堂設計的智能出場卷系統，支援老師上傳數學題目圖片，AI自動生成參考解答，學生透過手寫作答並獲得即時AI批改回饋。

## 技術架構

### 後端技術棧
- **Flask**: Python Web框架，提供RESTful API
- **SQLAlchemy**: ORM資料庫操作
- **SQLite**: 輕量級資料庫
- **OpenAI GPT-4o**: AI內容生成與批改
- **Pix2Text (P2T)**: 數學公式OCR辨識
- **Werkzeug**: 檔案上傳處理

### 前端技術棧
- **HTML5 + CSS3**: 響應式網頁設計
- **JavaScript (ES6+)**: 動態互動功能
- **Canvas API**: 手寫輸入處理
- **MathJax**: LaTeX數學公式渲染
- **QRCode.js**: QR碼生成

### 核心功能模組

## 1. 老師端功能

### 1.1 題目上傳與管理
**技術實現：**
- 支援拖拽、點擊、Ctrl+V多種上傳方式
- 檔案格式驗證：`ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}`
- 檔案大小限制：16MB
- 唯一檔名生成：`f"{uuid.uuid4()}_{filename}"`

**API端點：**
```python
@app.route('/api/upload_questions', methods=['POST'])
```

**處理流程：**
1. 接收多個圖片檔案
2. 使用P2T進行OCR文字辨識
3. 轉換為Base64格式供GPT-4o圖片API使用
4. 呼叫GPT-4o生成參考解答（max_tokens=1500）
5. 儲存到SQLite資料庫
6. 回傳解答預覽

### 1.2 AI參考解答生成
**技術細節：**
- **模型選擇**：GPT-4o（支援圖片）+ GPT-4-1106-preview（純文字）
- **Token限制**：1500 tokens確保完整解答
- **提示詞工程**：
  ```python
  prompt = f"請根據下列數學題目，詳細列出完整的解題步驟，最後明確給出標準答案。請用清楚的數學排版（如 LaTeX），並適當使用粗體標示重點。僅回傳解題過程與標準答案，不要額外解釋：\n題目：{q_text}"
  ```

**LaTeX處理：**
- 自動轉換 `\(...\)` → `$...$`
- 自動轉換 `\[...\]` → `$$...$$`
- MathJax渲染支援行內與區塊數學

### 1.3 題組管理
**功能特色：**
- 即時QR碼生成（使用Google Charts API備用）
- 學生連結分享
- 題組刪除與重置
- 管理員介面

**QR碼生成技術：**
```javascript
// 多重備用方案
const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(studentUrl)}`;
// 備用：Google Charts API
// 錯誤處理：顯示友善提示
```

## 2. 學生端功能

### 2.1 手寫輸入系統
**Canvas技術實現：**
- **畫布尺寸**：動態調整 `Math.min(window.innerWidth * 0.76, 720)`
- **觸控支援**：`touch-action: none`
- **繪圖模式**：畫筆/橡皮擦切換
- **即時繪製**：使用Pointer Events API

**繪圖演算法：**
```javascript
canvas.addEventListener('pointermove', e => {
    if (!drawing) return;
    const ctx = canvas.getContext('2d');
    ctx.lineWidth = erasing ? 24 : 4;
    ctx.lineCap = 'round';
    ctx.strokeStyle = erasing ? '#fff' : '#222';
    ctx.beginPath();
    ctx.moveTo(lastX, lastY);
    ctx.lineTo(e.offsetX, e.offsetY);
    ctx.stroke();
    [lastX, lastY] = [e.offsetX, e.offsetY];
});
```

### 2.2 AI批改系統
**技術架構：**
- **OCR辨識**：P2T識別手寫數學公式
- **AI批改**：GPT-4o分析解題邏輯
- **回饋生成**：max_tokens=1500確保完整回覆

**批改邏輯：**
```python
prompt = f"請以家教老師寬鬆的角度批改下列數學題目，重點在於學生的解題過程是否符合數學邏輯，不必要求與標準答案完全相同。只要學生的過程合理、有數學依據即可給予正面回饋。若學生有錯誤，請明確指出錯在哪一個步驟，並且一定要把正確的步驟詳細告訴他。請簡要說明理由。"
```

**回覆處理：**
- 自動滾動到結果區域
- 行內數學符號保持在同一行
- 完整內容顯示（無高度限制）

## 3. 資料庫設計

### 3.1 資料表結構
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
    image_path = db.Column(db.String(256), nullable=False)
    ocr_text = db.Column(db.Text)  # 無長度限制
    ai_answer = db.Column(db.Text)  # 無長度限制

class StudentAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    image_path = db.Column(db.String(256))
    ocr_text = db.Column(db.Text)  # 無長度限制
    ai_feedback = db.Column(db.Text)  # 無長度限制
    created_at = db.Column(db.DateTime, nullable=False)
```

### 3.2 資料流程
1. **題目上傳** → QuizSet + Question
2. **學生作答** → StudentAnswer
3. **AI批改** → 更新StudentAnswer.ai_feedback
4. **資料查詢** → 透過session_id關聯查詢

## 4. API設計

### 4.1 RESTful API端點
```
POST /api/upload_questions     # 老師上傳題目
POST /api/upload_answer        # 學生上傳答案
POST /api/reset               # 重置題組
GET  /api/get_questions       # 取得題目
GET  /api/all_quizsets        # 取得所有題組
GET  /uploads/<filename>      # 靜態檔案服務
```

### 4.2 錯誤處理
- **HTTP狀態碼**：400, 404, 500
- **JSON回應格式**：`{'error': '錯誤訊息'}` 或 `{'result': '成功結果'}`
- **異常捕獲**：try-catch包裝所有外部API呼叫

## 5. 前端技術細節

### 5.1 響應式設計
```css
.container { 
    max-width: 900px; 
    margin: 40px auto; 
    background: #fff; 
    border-radius: 16px; 
    box-shadow: 0 8px 32px rgba(0,0,0,0.08); 
    padding: 32px; 
}
```

### 5.2 MathJax配置
```javascript
window.MathJax = {
    tex: {
        inlineMath: [['$', '$'], ['\\(', '\\)']],
        displayMath: [['$$', '$$'], ['\\[', '\\]']]
    },
    options: {
        skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre']
    }
};
```

### 5.3 動態內容渲染
- **題目切換**：單頁應用模式
- **進度顯示**：實時更新題號
- **按鈕狀態**：動態啟用/禁用

## 6. 安全性考量

### 6.1 檔案安全
- **檔案類型驗證**：白名單機制
- **檔案大小限制**：防止DoS攻擊
- **唯一檔名**：避免路徑遍歷攻擊

### 6.2 資料安全
- **SQL注入防護**：使用ORM參數化查詢
- **XSS防護**：輸出轉義
- **CSRF防護**：表單驗證

## 7. 效能優化

### 7.1 前端優化
- **圖片壓縮**：Canvas toBlob
- **懶載入**：MathJax按需載入
- **快取策略**：靜態資源快取

### 7.2 後端優化
- **資料庫索引**：session_id索引
- **檔案清理**：定期清理暫存檔案
- **API限流**：防止濫用

## 8. 部署說明

### 8.1 環境需求
```bash
Python 3.11+
Flask 2.0+
OpenAI API Key
Pix2Text
```

### 8.2 安裝步驟
```bash
pip install -r requirements.txt
export OPENAI_API_KEY="your-api-key"
python main.py
```

### 8.3 生產環境配置
- **WSGI伺服器**：Gunicorn
- **反向代理**：Nginx
- **HTTPS**：SSL證書配置
- **資料庫**：PostgreSQL（可選）

## 9. 故障排除

### 9.1 常見問題
1. **AI回覆截斷**：檢查max_tokens設定
2. **QR碼不顯示**：檢查網路連線和API可用性
3. **手寫辨識失敗**：檢查P2T安裝和圖片品質
4. **MathJax渲染問題**：檢查LaTeX語法

### 9.2 調試工具
- **瀏覽器開發者工具**：前端調試
- **Flask Debug模式**：後端調試
- **資料庫查詢**：SQLite Browser

## 10. 未來擴展

### 10.1 功能擴展
- **多語言支援**：國際化
- **批量匯入**：Excel/CSV支援
- **統計分析**：學習數據分析
- **行動應用**：React Native

### 10.2 技術升級
- **微服務架構**：服務拆分
- **容器化部署**：Docker
- **雲端部署**：AWS/Azure
- **AI模型優化**：Fine-tuning

---

**系統版本**：v2.0  
**最後更新**：2024年12月  
**技術支援**：請參考GitHub Issues或聯繫開發團隊 