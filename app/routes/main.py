"""
examcat - 主页面路由蓝图
"""
from flask import Blueprint, render_template, redirect, url_for, flash
from datetime import datetime
from ..utils.auth import login_required, get_user_id
from ..utils.database import get_db, get_current_bank, get_current_question_id, get_bank_progress, get_last_unfinished_exam

main_bp = Blueprint('main', __name__, template_folder='../templates/base')

@main_bp.route('/')
@login_required
def index():
    """Home page route."""
    user_id = get_user_id()
    current_bank = get_current_bank(user_id)
    
    # 使用新的函数获取当前题目ID（确保属于当前题库）
    current_seq_qid = get_current_question_id(user_id)
    
    # 获取当前题库的进度信息
    progress_info = get_bank_progress(user_id, current_bank)

    # 获取当前未完成的考试ID
    last_unfinished_exam = get_last_unfinished_exam(user_id)
    last_unfinished_exam_id = last_unfinished_exam['id'] if last_unfinished_exam else None

    return render_template('index.html', 
                          current_year=datetime.now().year,
                          current_seq_qid=current_seq_qid,
                          current_bank=current_bank,
                          last_unfinished_exam_id = last_unfinished_exam_id,
                          answered=progress_info['answered'],
                          total=progress_info['total'],
                          progress_percentage=progress_info['progress'])

@main_bp.route('/reset_history', methods=['POST'])
@login_required
def reset_history():
    """Route to reset a user's answer history."""
    user_id = get_user_id()
    current_bank = get_current_bank(user_id)
    
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Delete only history for questions in current bank
        c.execute('''
            DELETE FROM history 
            WHERE user_id = ? 
              AND question_id IN (
                  SELECT id FROM questions WHERE bank_name = ?
              )
        ''', (user_id, current_bank))
        
        # Also clear the current sequential question ID
        # 注意：这里设置为NULL，下次调用get_current_question_id时会自动计算新的题目ID
        c.execute('UPDATE users SET current_seq_qid = NULL WHERE id = ?', (user_id,))
        conn.commit()
        
        flash("当前题库答题历史已重置。现在您可以重新开始答题。", "success")
    except Exception as e:
        flash(f"重置历史时出错: {str(e)}", "error")
        
    return redirect(url_for('questions.random_question'))