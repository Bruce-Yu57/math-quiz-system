import sys
print("啟動 main.py", file=sys.stderr)

from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for, session, send_file
import os
import uuid
import requests
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import base64
import openai
import time
import threading
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import io

# 載入 .env 設定
load_dotenv()

# 從環境變數讀取 p2t API 的 URL
P2T_API_URL = os.getenv('P2T_API_URL')

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 資料庫配置
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///math_quiz.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 載入 OpenAI API KEY
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY

# --- 資料表定義 ---
class QuizSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), unique=True, nullable=False)
    teacher = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    questions = db.relationship('Question', backref='quizset', lazy=True, cascade="all, delete-orphan")

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), db.ForeignKey('quiz_set.session_id'), nullable=False)
    idx = db.Column(db.Integer, nullable=False)
    image_path = db.Column(db.String(256), nullable=True)  # 保留相容舊資料
    image_blob = db.Column(db.LargeBinary)  # 新增，存圖檔 bytes
    ocr_text = db.Column(db.Text)
    ai_answer = db.Column(db.Text)
    answers = db.relationship('StudentAnswer', backref='question', lazy=True, cascade="all, delete-orphan")

class StudentAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    student_code = db.Column(db.String(64))
    image_path = db.Column(db.String(256))
    ocr_text = db.Column(db.Text)
    ai_feedback = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False)

# --- 輔助函式 ---

def call_p2t_api(filepath):
    """
    呼叫部署在外部的 p2t API 來進行圖片辨識。
    """
    if not P2T_API_URL:
        print("錯誤：P2T_API_URL 環境變數未設定。")
        return "[辨識服務未設定]"

    try:
        with open(filepath, 'rb') as f:
            files = {'file': (os.path.basename(filepath), f, 'image/png')}
            # 設定較長的超時時間，因為模型可能需要時間來處理
            response = requests.post(f"{P2T_API_URL}/recognize", files=files, timeout=60)
            response.raise_for_status() # 如果請求失敗 (狀態碼 4xx/5xx)，拋出異常
            data = response.json()
            if 'latex' in data:
                return data['latex']
            else:
                # API 回傳的 JSON 中沒有 'latex' 鍵
                print(f"p2t API 回應格式錯誤: {data.get('error', '未知錯誤')}")
                return f"[辨識失敗: {data.get('error', 'API回應格式錯誤')}]"
    except requests.exceptions.Timeout:
        print("呼叫 p2t API 時發生超時錯誤。")
        return "[辨識服務超時]"
    except requests.exceptions.RequestException as e:
        # 處理網路請求相關的錯誤 (如連線失敗)
        print(f"呼叫 p2t API 時發生網路錯誤: {e}")
        return f"[辨識服務連線失敗]"
    except Exception as e:
        # 處理其他所有預期外的錯誤
        print(f"呼叫 p2t API 時發生未知錯誤: {e}")
        return f"[辨識服務發生未知錯誤]"

def recognize_printed_question(filepath, img_b64):
    """
    使用 GPT-4o 進行印刷題目辨識。
    """
    try:
        prompt = "請仔細辨識這張圖片中的數學題目，將所有文字、數字、符號和公式完整地轉錄出來。請保持原始格式，包括換行和空格。如果圖片中有多個題目，請用換行分隔。"
        
        messages = [
            {"role": "system", "content": "你是一個專業的數學題目辨識助手，請準確地將圖片中的數學題目轉錄為文字。"},
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
            ]}
        ]
        
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=1000
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"GPT-4o 題目辨識失敗: {e}")
        return f"[題目辨識失敗: {e}]"

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Flask 路由 ---

@app.route('/')
def teacher_index():
    return render_template('teacher.html')

@app.route('/student/<session_id>')
def student_index(session_id):
    return render_template('student.html', session_id=session_id)

@app.route('/api/upload_questions', methods=['POST'])
def upload_questions():
    teacher = request.form.get('teacher', '未填寫')
    files = request.files.getlist('images')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': '沒有上傳任何圖片'}), 400
    if len(files) > 5:
        return jsonify({'error': '最多只能上傳5題'}), 400

    questions_data = []
    answers_data = []
    img_b64_list = []

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)

            with open(filepath, 'rb') as f_read:
                img_bytes = f_read.read()
                img_b64 = base64.b64encode(img_bytes).decode('utf-8')
                img_b64_list.append(img_b64)

            # 使用 GPT-4o 進行印刷題目辨識
            q_text = recognize_printed_question(filepath, img_b64)
            # 新增：先不再用 image_path，直接存 image_blob
            question_data = {'type': 'img', 'content': None, 'text': q_text, 'image_path': unique_filename, 'img_bytes': img_bytes}
            questions_data.append(question_data)

    if not questions_data:
        return jsonify({'error': '上傳的檔案格式不符或處理失敗'}), 400

    # 呼叫 GPT 產生參考解答
    def get_gpt_answer(q_text, img_b64):
        prompt = f"請根據下列數學題目，詳細列出完整的解題步驟，最後明確給出標準答案。請用清楚的數學排版（如 LaTeX），並適當使用粗體標示重點。僅回傳解題過程與標準答案，不要額外解釋：\n題目：{q_text}"
        try:
            model_to_use = "gpt-4o" if img_b64 else "gpt-4-1106-preview"
            messages = [
                {"role": "system", "content": "你是數學老師，請根據題目圖片與辨識文字，詳細列出完整的解題步驟與標準答案。"},
                {"role": "user", "content": [{"type": "text", "text": prompt}]}
            ]
            if img_b64:
                 messages[1]["content"].append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}})

            response = openai.chat.completions.create(model=model_to_use, messages=messages, max_tokens=1500)
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"[AI產生失敗: {e}]"

    for i, q in enumerate(questions_data):
        ans = get_gpt_answer(q['text'], img_b64_list[i])
        answers_data.append({'question': q['text'], 'answer': ans})

    # 寫入資料庫
    session_id = str(uuid.uuid4())
    quizset = QuizSet(session_id=session_id, teacher=teacher, created_at=datetime.now(), is_active=True)
    db.session.add(quizset)
    db.session.commit()

    for i, q in enumerate(questions_data):
        # 新增題目時，先寫入 DB 取得 id
        question = Question(
            session_id=session_id,
            idx=i,
            image_path=q['image_path'],
            image_blob=q['img_bytes'],
            ocr_text=q['text'],
            ai_answer=answers_data[i]['answer']
        )
        db.session.add(question)
        db.session.commit()  # 取得 question.id
        # 回傳給前端的 content 改為 API 連結
        q['content'] = f'/api/image/{question.id}'

    return jsonify({
        'answers': [
            {
                'question': q['text'],
                'answer': answers_data[i]['answer'],
                'content': q['content']
            } for i, q in enumerate(questions_data)
        ],
        'session_id': session_id,
        'questions': [
            {'type': 'img', 'content': q['content'], 'text': q['text']} for q in questions_data
        ]
    })


@app.route('/api/upload_answer', methods=['POST'])
def upload_answer():
    session_id = request.form.get('session_id')
    q_idx = request.form.get('q_idx')
    file = request.files.get('image')

    if not all([session_id, q_idx is not None, file]):
        return jsonify({'error': '缺少必要參數 (session_id, q_idx, image)'}), 400
    
    try:
        q_idx = int(q_idx)
    except ValueError:
        return jsonify({'error': '題號格式錯誤'}), 400

    question = Question.query.filter_by(session_id=session_id, idx=q_idx).first()
    if not question:
        return jsonify({'error': '查無此題目'}), 404

    filename = f"stu_{uuid.uuid4()}.png"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # 改為呼叫外部 API 進行辨識
    stu_latex = call_p2t_api(filepath)
    
    # 檢查辨識結果是否成功
    if stu_latex.startswith('[辨識服務') or stu_latex.startswith('[辨識失敗'):
        gpt_result = f"手寫辨識失敗：{stu_latex}\n\n請重新手寫答案並再次提交。"
    else:
        ref_answer = question.ai_answer or ''
        question_text = question.ocr_text or ''
        # 新增：先顯示學生辨識結果
        latex_display = f"【學生辨識結果（LaTeX）】\n{stu_latex}\n\n"
        prompt = f"請以家教老師寬鬆的角度批改下列數學題目，重點在於學生的解題過程是否符合數學邏輯，不必要求與標準答案完全相同。只要學生的過程合理、有數學依據即可給予正面回饋。若學生有錯誤，請明確指出錯在哪一個步驟，並且一定要把正確的步驟詳細告訴他。請簡要說明理由。\n題目：{question_text}\n標準解答：{ref_answer}\n學生答案（LaTeX）：{stu_latex}"
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "你是數學家教老師，批改時請以寬鬆、鼓勵、重邏輯不重格式的角度，學生只要過程合理即可給予正面回饋，不必要求與標準答案完全一致。若學生有錯誤，請明確指出錯在哪一個步驟，並且一定要把正確的步驟詳細告訴他。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500
            )
            gpt_result = latex_display + response.choices[0].message.content.strip()
        except Exception as e:
            gpt_result = latex_display + f"[AI批改失敗: {e}]"

    # 寫入學生作答紀錄
    stu_answer = StudentAnswer(
        session_id=session_id,
        question_id=question.id,
        image_path=filename,
        ocr_text=stu_latex,
        ai_feedback=gpt_result,
        created_at=datetime.now()
    )
    db.session.add(stu_answer)
    db.session.commit()

    return jsonify({'result': gpt_result})


@app.route('/api/get_questions')
def get_questions():
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({'error': '需要 session_id'}), 400
        
    questions = Question.query.filter_by(session_id=session_id).order_by(Question.idx).all()
    if not questions:
        return jsonify({'error': '查無此 session'}), 404
    
    q_list = [{'type': 'img', 'content': f'/uploads/{q.image_path}', 'text': q.ocr_text} for q in questions]
    return jsonify({'questions': q_list})


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# --- 管理後台 ---
@app.route('/admin')
def admin():
    return render_template('teacher_admin.html')

@app.route('/api/all_quizsets')
def all_quizsets():
    quizsets = QuizSet.query.order_by(QuizSet.created_at.desc()).all()
    result = []
    for q_set in quizsets:
        # 為了提高效率，我們只取回必要的資訊
        result.append({
            'session_id': q_set.session_id,
            'teacher': q_set.teacher,
            'created_at': q_set.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    return jsonify(result)

@app.route('/api/delete_session', methods=['POST'])
def delete_session():
    session_id = request.form.get('session_id')
    if not session_id:
        return jsonify({'status': 'error', 'msg': '缺少 session_id'}), 400

    quiz_set = QuizSet.query.filter_by(session_id=session_id).first()
    if not quiz_set:
        return jsonify({'status': 'error', 'msg': '找不到指定的題組'}), 404

    try:
        # 找出所有相關圖片並刪除
        questions = Question.query.filter_by(session_id=session_id).all()
        for q in questions:
            if q.image_path and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], q.image_path)):
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], q.image_path))
            
            student_answers = StudentAnswer.query.filter_by(question_id=q.id).all()
            for sa in student_answers:
                if sa.image_path and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], sa.image_path)):
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], sa.image_path))

        # 從資料庫刪除紀錄 (關聯的 Question 和 StudentAnswer 會自動級聯刪除)
        db.session.delete(quiz_set)
        db.session.commit()
        
        return jsonify({'status': 'success', 'msg': '題組已成功刪除'})
    except Exception as e:
        db.session.rollback()
        print(f"刪除題組時發生錯誤: {e}")
        return jsonify({'status': 'error', 'msg': f'刪除失敗: {e}'}), 500

@app.route('/api/image/<int:question_id>')
def get_question_image(question_id):
    q = Question.query.get_or_404(question_id)
    if q.image_blob:
        return send_file(io.BytesIO(q.image_blob), mimetype='image/png')
    elif q.image_path:
        # 相容舊資料
        return send_from_directory(app.config['UPLOAD_FOLDER'], q.image_path)
    else:
        return '', 404

def init_db():
    with app.app_context():
        print("正在檢查並建立資料庫表格...")
        db.create_all()
        print("資料庫表格已創建。")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=10000)
