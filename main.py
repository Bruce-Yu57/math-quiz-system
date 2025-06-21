from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for, session
from pix2text import Pix2Text
import os
import uuid
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import base64
import openai
import time
import threading
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# 載入 .env 設定
load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 資料庫配置 - 支援本地開發和Render部署
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    # Render PostgreSQL 配置
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    # 本地開發 SQLite 配置
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///math_quiz.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 資料表定義
class QuizSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), unique=True, nullable=False)
    teacher = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    questions = db.relationship('Question', backref='quizset', lazy=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), db.ForeignKey('quiz_set.session_id'), nullable=False)
    idx = db.Column(db.Integer, nullable=False)
    image_path = db.Column(db.String(256), nullable=False)
    ocr_text = db.Column(db.Text)
    ai_answer = db.Column(db.Text)
    answers = db.relationship('StudentAnswer', backref='question', lazy=True)

class StudentAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    student_code = db.Column(db.String(64))
    image_path = db.Column(db.String(256))
    ocr_text = db.Column(db.Text)
    ai_feedback = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False)

# 全域 p2t 實例，初始為 None
p2t = None

def get_p2t():
    """
    延遲載入函式 (Lazy Loading)。
    第一次呼叫時才初始化 Pix2Text 模型，之後直接回傳已建立的實例。
    """
    global p2t
    if p2t is None:
        # 為了讓 Render 知道服務正在啟動，我們在這裡印出日誌
        print("Initializing Pix2Text model for the first time. This may take a moment...")
        p2t = Pix2Text()
        print("Pix2Text model initialized successfully.")
    return p2t

# 允許的檔案格式
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}

# session 資料暫存（簡單用 dict，正式可用 DB）
sessions = {}

# 載入 OpenAI API KEY
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ===== 老師端首頁 =====
@app.route('/')
def teacher_index():
    return render_template('teacher.html')

# ===== 學生端首頁（動態產生 QR code 導向） =====
@app.route('/student/<session_id>')
def student_index(session_id):
    return render_template('student.html', session_id=session_id)

# ===== 題目上傳 API（老師端） =====
@app.route('/api/upload_questions', methods=['POST'])
def upload_questions():
    teacher = request.form.get('teacher', '未填寫')
    files = request.files.getlist('images')
    if not files or len(files) == 0:
        return jsonify({'error': '沒有上傳任何圖片'}), 400
    if len(files) > 5:
        return jsonify({'error': '最多只能上傳5題'}), 400

    questions = []
    answers = []
    img_b64_list = []
    for file in files:
        # 儲存圖片
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        # 轉 base64 供 GPT-4o 圖片 API 用
        with open(filepath, 'rb') as f:
            img_bytes = f.read()
            img_b64 = base64.b64encode(img_bytes).decode('utf-8')
            img_b64_list.append(img_b64)
        # 用 p2t 辨識題目文字
        try:
            # 透過 get_p2t() 取得辨識器
            recognizer = get_p2t()
            q_text = recognizer.recognize(filepath)
        except Exception as e:
            q_text = ''
        questions.append({'type': 'img', 'content': f'/uploads/{unique_filename}', 'text': q_text, 'image_path': unique_filename})
        # 圖片暫時不刪除，供學生端顯示

    # 呼叫 GPT-4o 產生參考解答
    def get_gpt_answer(q_text, img_b64=None):
        prompt = f"請根據下列數學題目，詳細列出完整的解題步驟，最後明確給出標準答案。請用清楚的數學排版（如 LaTeX），並適當使用粗體標示重點。僅回傳解題過程與標準答案，不要額外解釋：\n題目：{q_text}"
        if img_b64:
            try:
                response = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "你是數學老師，請根據題目圖片與辨識文字，詳細列出完整的解題步驟與標準答案。"},
                        {"role": "user", "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
                        ]}
                    ],
                    max_tokens=1500
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                return f"[AI產生失敗: {e}]"
        else:
            try:
                response = openai.chat.completions.create(
                    model="gpt-4-1106-preview",
                    messages=[
                        {"role": "system", "content": "你是數學老師，請根據題目詳細列出完整的解題步驟與標準答案。"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1500
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                return f"[AI產生失敗: {e}]"

    # 串行產生答案（可改為多執行緒加速）
    for idx, q in enumerate(questions):
        ans = get_gpt_answer(q['text'], img_b64_list[idx])
        answers.append({'question': q['text'], 'answer': ans})

    # 產生 session_id 並寫入資料庫
    session_id = str(uuid.uuid4())
    quizset = QuizSet(session_id=session_id, teacher=teacher, created_at=datetime.now(), is_active=True)
    db.session.add(quizset)
    db.session.commit()
    # 寫入每一題
    for idx, q in enumerate(questions):
        question = Question(
            session_id=session_id,
            idx=idx,
            image_path=q['image_path'],
            ocr_text=q['text'],
            ai_answer=answers[idx]['answer']
        )
        db.session.add(question)
    db.session.commit()

    return jsonify({'answers': answers, 'session_id': session_id})

# ===== 學生作答上傳 API =====
@app.route('/api/upload_answer', methods=['POST'])
def upload_answer():
    session_id = request.form.get('session_id')
    q_idx = request.form.get('q_idx')
    file = request.files.get('image')
    if not session_id:
        return jsonify({'error': '查無此題目，請重新掃描 QR code'}), 400
    if q_idx is None or not file:
        return jsonify({'error': '缺少題號或圖片'}), 400
    try:
        q_idx = int(q_idx)
    except:
        return jsonify({'error': '題號格式錯誤'}), 400
    # 查詢題目
    question = Question.query.filter_by(session_id=session_id, idx=q_idx).first()
    if not question:
        return jsonify({'error': '查無此題目，請重新掃描 QR code'}), 400
    # 儲存學生答案圖片
    filename = f"stu_{uuid.uuid4()}.png"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    # 用 p2t 辨識學生答案
    try:
        # 透過 get_p2t() 取得辨識器
        recognizer = get_p2t()
        stu_latex = recognizer.recognize(filepath)
    except Exception as e:
        stu_latex = ''
    # 取得參考解答
    ref_answer = question.ai_answer or ''
    question_text = question.ocr_text or ''
    # 呼叫 GPT-4o 批改
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
        gpt_result = response.choices[0].message.content.strip()
        # 添加調試信息
        print(f"AI批改回覆長度: {len(gpt_result)} 字符")
        print(f"AI批改回覆內容: {gpt_result[:200]}...")  # 只顯示前200字符
    except Exception as e:
        gpt_result = f"[AI批改失敗: {e}]"
        print(f"AI批改失敗: {e}")
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
    
    # 確認儲存到資料庫的內容
    saved_feedback = stu_answer.ai_feedback
    print(f"儲存到資料庫的回覆長度: {len(saved_feedback)} 字符")
    print(f"儲存到資料庫的回覆內容: {saved_feedback[:200]}...")
    
    # 回傳批改結果
    response_data = {'result': gpt_result, 'stu_latex': stu_latex}
    print(f"回傳給前端的回覆長度: {len(gpt_result)} 字符")
    print(f"回傳給前端的回覆內容: {gpt_result[:200]}...")
    return jsonify(response_data)

# ===== 重新出題 API =====
@app.route('/api/reset', methods=['POST'])
def reset():
    session_id = request.form.get('session_id')
    if not session_id:
        return jsonify({'error': '缺少 session_id'}), 400
    # 先刪除該 session_id 的學生作答
    questions = Question.query.filter_by(session_id=session_id).all()
    for q in questions:
        StudentAnswer.query.filter_by(question_id=q.id).delete()
    # 再刪除該 session_id 的題目
    Question.query.filter_by(session_id=session_id).delete()
    # 最後刪除該 session_id 的 QuizSet
    QuizSet.query.filter_by(session_id=session_id).delete()
    db.session.commit()
    return jsonify({'msg': f'session_id={session_id} 的題目與答案已清空'})

# ===== 取得題目 API =====
@app.route('/api/get_questions')
def get_questions():
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({'error': '查無此題目，請確認 QR code 是否正確'}), 404
    questions = Question.query.filter_by(session_id=session_id).order_by(Question.idx).all()
    if not questions:
        return jsonify({'error': '查無此題目，請確認 QR code 是否正確'}), 404
    # 只回傳題目內容（不含答案）
    return jsonify({'questions': [{'type': 'img', 'content': f'/uploads/{q.image_path}'} for q in questions]})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ===== 題組管理 API =====
@app.route('/api/all_quizsets')
def all_quizsets():
    quizsets = QuizSet.query.order_by(QuizSet.created_at.desc()).all()
    return jsonify([
        {
            'id': q.id,
            'teacher': q.teacher,
            'session_id': q.session_id,
            'created_at': q.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        for q in quizsets
    ])

# ===== 題組管理頁面 =====
@app.route('/admin')
def admin():
    return render_template('teacher_admin.html')

# 資料庫初始化
def init_db():
    with app.app_context():
        db.create_all()
        print("資料庫表格已創建")

if __name__ == '__main__':
    # 初始化資料庫
    init_db()
    # 本地開發模式
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port) 