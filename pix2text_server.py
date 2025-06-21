from flask import Flask, request, jsonify
from pix2text.math_formula import MathFormulaRecognizer

app = Flask(__name__)
mfr = MathFormulaRecognizer()  # 只載入數學式模型

@app.route('/predict', methods=['POST'])
def predict():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    file = request.files['image']
    img_bytes = file.read()
    # 只做數學式辨識
    result = mfr.recognize(img_bytes)
    return jsonify({'latex': result})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)