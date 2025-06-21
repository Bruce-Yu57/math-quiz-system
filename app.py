from flask import Flask, request, jsonify, render_template, send_from_directory
from pix2text import Pix2Text
import os
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# 確保上傳資料夾存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 初始化 pix2text 辨識器
p2t = Pix2Text()

# 允許的檔案格式
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'image' not in request.files:
        return jsonify({'error': '沒有上傳圖片檔案'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': '沒有選擇檔案'}), 400
    
    if file and allowed_file(file.filename):
        # 生成唯一檔名
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        # 儲存檔案
        file.save(filepath)
        
        try:
            # 使用 pix2text 進行數學式辨識
            result = p2t.recognize(filepath)
            
            return jsonify({
                'success': True,
                'latex': result,
                'filename': unique_filename
            })
            
        except Exception as e:
            return jsonify({'error': f'辨識過程中發生錯誤: {str(e)}'}), 500
        
        finally:
            # 清理暫存檔案
            if os.path.exists(filepath):
                os.remove(filepath)
    
    return jsonify({'error': '不支援的檔案格式'}), 400

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 