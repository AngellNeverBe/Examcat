"""
examcat - API路由蓝图（RESTful API）
"""
from flask import Blueprint, request, jsonify
from ..utils.auth import login_required, get_user_id
from ..utils.database import get_db, get_current_bank
from ..utils.questions import fetch_question

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/questions', methods=['GET'])
@login_required
def get_questions():
    """获取题目列表API"""
    user_id = get_user_id()
    current_bank = get_current_bank(user_id)
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    conn = get_db()
    c = conn.cursor()
    
    # 获取总数
    c.execute('SELECT COUNT(*) as total FROM questions WHERE bank_name = ?', (current_bank,))
    total = c.fetchone()['total']
    
    # 获取题目
    offset = (page - 1) * per_page
    c.execute('''
        SELECT id, stem, answer, difficulty, qtype, category
        FROM questions 
        WHERE bank_name = ?
        ORDER BY CAST(id AS INTEGER) ASC 
        LIMIT ? OFFSET ?
    ''', (current_bank, per_page, offset))
    
    questions = []
    for row in c.fetchall():
        questions.append({
            'id': row['id'],
            'stem': row['stem'],
            'answer': row['answer'],
            'difficulty': row['difficulty'],
            'type': row['qtype'],
            'category': row['category']
        })
    
    return jsonify({
        'success': True,
        'data': questions,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': (total + per_page - 1) // per_page
        }
    })

@api_bp.route('/question/<qid>', methods=['GET'])
@login_required
def get_question(qid):
    """获取单个题目详情API"""
    q = fetch_question(qid)
    
    if not q:
        return jsonify({
            'success': False,
            'error': '题目不存在'
        }), 404
    
    return jsonify({
        'success': True,
        'data': q
    })

@api_bp.route('/submit', methods=['POST'])
@login_required
def submit_answer():
    """提交答案API"""
    user_id = get_user_id()
    data = request.get_json()
    
    if not data or 'question_id' not in data or 'answer' not in data:
        return jsonify({
            'success': False,
            'error': '缺少参数'
        }), 400
    
    question_id = data['question_id']
    user_answer = data['answer']
    
    q = fetch_question(question_id)
    if not q:
        return jsonify({
            'success': False,
            'error': '题目不存在'
        }), 404
    
    # 处理答案（支持多选）
    if isinstance(user_answer, list):
        user_answer_str = "".join(sorted(user_answer))
    else:
        user_answer_str = str(user_answer)
    
    correct_answer = "".join(sorted(q['answer']))
    is_correct = user_answer_str == correct_answer
    
    # 保存到历史
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO history (user_id, question_id, user_answer, correct) 
        VALUES (?,?,?,?)
    ''', (user_id, question_id, user_answer_str, 1 if is_correct else 0))
    conn.commit()    
    
    return jsonify({
        'success': True,
        'is_correct': is_correct,
        'correct_answer': q['answer'],
        'explanation': f"正确答案：{q['answer']}"
    })

@api_bp.route('/statistics', methods=['GET'])
@login_required
def get_statistics():
    """获取统计信息API"""
    user_id = get_user_id()
    current_bank = get_current_bank(user_id)
    
    conn = get_db()
    c = conn.cursor()
    
    # 总体统计
    c.execute('''
        SELECT 
            COUNT(*) as total_answered,
            SUM(correct) as correct_count
        FROM history h 
        JOIN questions q ON h.question_id = q.id
        WHERE h.user_id = ? AND q.bank_name = ?
    ''', (user_id, current_bank))
    
    stats = c.fetchone()
    total_answered = stats['total_answered'] or 0
    correct_count = stats['correct_count'] or 0
    
    overall_accuracy = (correct_count / total_answered * 100) if total_answered > 0 else 0
    
    return jsonify({
        'success': True,
        'data': {
            'total_answered': total_answered,
            'correct_count': correct_count,
            'accuracy': round(overall_accuracy, 2),
            'current_bank': current_bank
        }
    })

@api_bp.route('/favorites', methods=['GET'])
@login_required
def get_favorites():
    """获取收藏列表API"""
    user_id = get_user_id()
    current_bank = get_current_bank(user_id)
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT f.question_id, f.tag, q.stem
        FROM favorites f 
        JOIN questions q ON f.question_id=q.id 
        WHERE f.user_id=? AND q.bank_name = ?
        ORDER BY f.created_at DESC
    ''', (user_id, current_bank))
    
    favorites = []
    for r in c.fetchall():
        favorites.append({
            'question_id': r['question_id'],
            'tag': r['tag'],
            'stem': r['stem']
        })
    
    return jsonify({
        'success': True,
        'data': favorites
    })

@api_bp.route('/banks', methods=['GET'])
def get_banks():
    """获取题库列表API"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT bank_name, COUNT(*) as question_count
        FROM questions
        GROUP BY bank_name
        ORDER BY bank_name
    ''')
    
    banks = []
    for r in c.fetchall():
        banks.append({
            'name': r['bank_name'],
            'question_count': r['question_count']
        })
    
    return jsonify({
        'success': True,
        'data': banks
    })