# p2t_api_server.py
import os
from flask import Flask, request, jsonify
from pix2text import Pix2Text
import logging
from PIL import Image
import io

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 初始化 Pix2Text 模型
# 這會在第一次啟動時下載模型檔案，可能會需要一點時間
try:
    logger.info("正在初始化 Pix2Text 手寫專用模型 (mfr)...")
    p2t = Pix2Text(model_type='mfr')
    logger.info("Pix2Text mfr 模型初始化完成。")
except Exception as e:
    logger.error(f"模型初始化失敗: {e}", exc_info=True)
    p2t = None

@app.route('/recognize', methods=['POST'])
def recognize():
    if p2t is None:
        return jsonify({'error': '模型未成功初始化，請檢查伺服器日誌。'}), 500

    if 'file' not in request.files:
        return jsonify({'error': '請求中沒有找到檔案部分'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': '沒有選擇檔案'}), 400
        
    try:
        # 讀取圖片檔案的 bytes
        img_bytes = file.read()
        # DEBUG: 將收到的圖片存檔
        # with open("debug_upload.png", "wb") as f:
        #     f.write(img_bytes)
        logger.info(f"收到圖片: {file.filename}, 大小: {len(img_bytes)} bytes")
        # 將 bytes 轉成 PIL Image
        try:
            img = Image.open(io.BytesIO(img_bytes))
            # 圖片預處理：轉灰階、二值化
            img = img.convert('L')  # 轉灰階
            img = img.point(lambda x: 0 if x < 200 else 255, '1')  # 二值化，閾值可調整
        except Exception as e:
            logger.error(f'無法將 bytes 轉為圖片: {e}', exc_info=True)
            return jsonify({'error': '圖片格式錯誤，無法辨識。'}), 400
        # 使用 Pix2Text 進行辨識
        outs = p2t.recognize(img)
        # 判斷結果型態
        if isinstance(outs, list) and all(isinstance(out, dict) and 'text' in out for out in outs):
            latex_str = " ".join([out['text'] for out in outs])
            logger.info(f"辨識結果: {latex_str}")
            return jsonify({'latex': latex_str})
        elif isinstance(outs, str):
            logger.info(f"辨識結果(字串): {outs}")
            return jsonify({'latex': outs})
        else:
            logger.error(f"Pix2Text 辨識回傳非預期格式: {outs}")
            return jsonify({'error': f'辨識失敗: {outs}'}), 500
        
    except Exception as e:
        logger.error(f"圖片辨識時發生錯誤: {e}", exc_info=True)
        return jsonify({'error': '辨識過程中發生內部錯誤。'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """簡單的健康檢查端點"""
    if p2t:
        return jsonify({'status': 'ok', 'model_loaded': True}), 200
    else:
        return jsonify({'status': 'error', 'model_loaded': False}), 500

if __name__ == '__main__':
    # 監聽所有網路介面，讓區域網路中的其他電腦可以連線
    # 端口可以自訂，例如 5001
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=False, host='0.0.0.0', port=port) 