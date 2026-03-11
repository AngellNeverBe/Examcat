"""
examcat - 统计路由蓝图
"""
from flask import Blueprint, render_template, flash, redirect, url_for
import json
from ..utils.auth import login_required, get_user_id
from ..utils.database import get_db, get_current_bank
from ..utils.questions import fetch_question

statistics_bp = Blueprint('statistics', __name__, url_prefix='/stats', template_folder='../templates/base')

@statistics_bp.route('/')
@login_required
def show():
    """显示统计信息"""
    user_id = get_user_id()
    current_bank = get_current_bank(user_id)
    conn = get_db()
    c = conn.cursor()
    
    # 当前题库总体正确率
    c.execute('''
        SELECT 
            COUNT(*) as total, 
            SUM(h.correct) as correct_count 
        FROM history h 
        JOIN questions q ON h.question_id = q.id
        WHERE h.user_id = ? AND q.bank_name = ?
    ''', (user_id, current_bank))
    
    row = c.fetchone()
    total = row['total'] if row['total'] else 0
    correct_count = row['correct_count'] if row['correct_count'] else 0
    wrong_count = total - correct_count
    overall_accuracy = (correct_count/total*100) if total>0 else 0
    
    # 按难度统计
    c.execute('''
        SELECT 
            q.difficulty, 
            COUNT(*) as total, 
            SUM(h.correct) as correct_count
        FROM history h 
        JOIN questions q ON h.question_id=q.id
        WHERE h.user_id = ? AND q.bank_name = ?
        GROUP BY q.difficulty
    ''', (user_id, current_bank))
    
    difficulty_stats = []
    for r in c.fetchall():
        difficulty_stats.append({
            'difficulty': r['difficulty'] or '未分类',
            'total': r['total'],
            'correct_count': r['correct_count'],
            'accuracy': (r['correct_count']/r['total']*100) if r['total']>0 else 0
        })
    
    # 按类别统计
    c.execute('''
        SELECT 
            q.category, 
            COUNT(*) as total, 
            SUM(h.correct) as correct_count
        FROM history h 
        JOIN questions q ON h.question_id=q.id
        WHERE h.user_id = ? AND q.bank_name = ?
        GROUP BY q.category
    ''', (user_id, current_bank))
    
    category_stats = []
    for r in c.fetchall():
        category_stats.append({
            'category': r['category'] or '未分类',
            'total': r['total'],
            'correct_count': r['correct_count'],
            'accuracy': (r['correct_count']/r['total']*100) if r['total']>0 else 0
        })
    
    # 最多错误的题目
    c.execute('''
        SELECT 
            h.question_id, 
            COUNT(*) as wrong_times, 
            q.stem
        FROM history h 
        JOIN questions q ON h.question_id=q.id
        WHERE h.user_id = ? AND h.correct = 0 AND q.bank_name = ?
        GROUP BY h.question_id
        ORDER BY wrong_times DESC
        LIMIT 10
    ''', (user_id, current_bank))
    
    worst_questions = []
    for r in c.fetchall():
        worst_questions.append({
            'question_id': r['question_id'],
            'stem': r['stem'],
            'wrong_times': r['wrong_times']
        })
    
    # 获取考试历史
    c.execute('''
        SELECT * FROM exam_sessions 
        WHERE user_id = ? AND completed = 1 
        ORDER BY start_time DESC
        LIMIT 10
    ''', (user_id,))
    
    exam_history = []
    for r in c.fetchall():
        exam_history.append({
            'id': r['id'],
            'mode': r['mode'],
            'score': r['score'],
            'start_time': r['start_time'],
            'duration': r['duration']
        })
    
    return render_template('statistics.html', 
                          total=total,
                          correct_count=correct_count,
                          wrong_count=wrong_count,
                          overall_accuracy=overall_accuracy,
                          difficulty_stats=difficulty_stats,
                          category_stats=category_stats,
                          worst_questions=worst_questions,
                          exam_history=exam_history,
                          current_bank=current_bank)

@statistics_bp.route('/exam/<int:exam_id>')
@login_required
def exam_detail(exam_id):
    """查看考试详情"""
    user_id = get_user_id()
    
    conn = get_db()
    c = conn.cursor()
    
    # 获取考试信息
    c.execute('SELECT * FROM exam_sessions WHERE id=? AND user_id=?', (exam_id, user_id))
    exam = c.fetchone()
    
    if not exam:
        
        flash("无法找到考试记录", "error")
        return redirect(url_for('statistics.show'))
    
    # 获取题目详情
    question_ids = json.loads(exam['question_ids'])
    questions = []
    
    for qid in question_ids:
        q = fetch_question(qid)
        if q:
            questions.append(q)
    
    
    
    return render_template('exam_detail.html', 
                          exam=exam,
                          questions=questions,
                          current_bank=get_current_bank(user_id))