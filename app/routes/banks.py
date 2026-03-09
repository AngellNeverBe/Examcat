"""
examcat - 题库管理路由蓝图
"""
import os
import csv
from flask import Blueprint, render_template, request, flash, redirect, url_for
from ..utils.auth import login_required, get_user_id, admin_required
from ..utils.database import get_db, get_available_banks, get_current_bank, set_current_bank, load_questions_to_db

banks_bp = Blueprint('banks', __name__, template_folder='../templates/base')

def get_bank_question_count_from_csv(bank_name):
    """
    从CSV文件获取题库的题目总数。
    这个方法用于当题库尚未加载到数据库时的备用统计。
    """
    try:
        # 确保bank_name有.csv后缀来查找文件
        if not bank_name.endswith('.csv'):
            file_name = bank_name + '.csv'
        else:
            file_name = bank_name
            bank_name = bank_name[:-4]  # 去掉.csv后缀存储
        
        bank_path = os.path.join('./questions-bank', file_name)
        
        if not os.path.exists(bank_path):
            return 0
        
        with open(bank_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            # 跳过标题行
            next(reader, None)
            # 统计行数
            count = sum(1 for row in reader)
            return count
    except Exception as e:
        print(f"Error reading CSV {bank_name}: {e}")
        return 0

@banks_bp.route('/select_bank')
@login_required
def select_bank():
    """Route to select a question bank."""
    user_id = get_user_id()
    current_bank = get_current_bank(user_id)
    available_banks = get_available_banks()
    
    # Get question count for each bank
    bank_stats = []
    conn = get_db()
    c = conn.cursor()
    
    for bank in available_banks:
        # 方法1：从数据库获取总题数
        c.execute('SELECT COUNT(*) as count FROM questions WHERE bank_name = ?', (bank,))
        count_row = c.fetchone()
        total_from_db = count_row['count'] if count_row else 0
        
        # 如果数据库中没有该题库的记录，从CSV文件读取
        total = total_from_db
        if total == 0:
            total = get_bank_question_count_from_csv(bank)
        
        # 修复：使用更准确的查询统计已答题数
        c.execute('''
            SELECT COUNT(DISTINCT h.question_id) as answered 
            FROM history h
            JOIN questions q ON h.question_id = q.id
            WHERE h.user_id = ? AND q.bank_name = ?
        ''', (user_id, bank))
        answered_row = c.fetchone()
        answered = answered_row['answered'] if answered_row else 0
        
        # 如果题库在数据库中不存在但CSV文件存在，可能需要加载
        needs_loading = total_from_db == 0 and total > 0
        
        bank_stats.append({
            'name': bank,
            'total': total,
            'answered': answered,
            'is_current': bank == current_bank,
            'needs_loading': needs_loading,
            'progress_percentage': round((answered / total * 100), 2) if total > 0 else 0
        })
    
    
    
    return render_template('select_bank.html', 
                          banks=bank_stats,
                          current_bank=current_bank)

@banks_bp.route('/load_bank', methods=['POST'])
@login_required
def load_bank():
    """Route to load a selected question bank."""
    user_id = get_user_id()
    bank_name = request.form.get('bank_name')
    
    if not bank_name:
        flash("请选择题库", "error")
        return redirect(url_for('banks.select_bank'))
    
    # Check if bank exists
    available_banks = get_available_banks()
    if bank_name not in available_banks:
        flash("题库不存在", "error")
        return redirect(url_for('banks.select_bank'))
    
    try:
        # Set current bank for user
        set_current_bank(user_id, bank_name)        
        # Load questions from the selected bank
        conn = get_db()
        load_questions_to_db(conn, bank_name)
        
        
        flash(f"已切换到题库: {bank_name}", "success")
    except Exception as e:
        flash(f"加载题库时出错: {str(e)}", "error")
    
    return redirect(url_for('main.index'))

@banks_bp.route('/upload_bank', methods=['POST'])
@admin_required
def upload_bank():
    """Route to upload a new question bank CSV file."""
    if 'bank_file' not in request.files:
        flash("没有选择文件", "error")
        return redirect(url_for('banks.select_bank'))
    
    file = request.files['bank_file']
    if file.filename == '':
        flash("没有选择文件", "error")
        return redirect(url_for('banks.select_bank'))
    
    if not file.filename.endswith('.csv'):
        flash("只支持CSV格式文件", "error")
        return redirect(url_for('banks.select_bank'))
    
    try:
        # Save the uploaded file
        banks_dir = './questions-bank'
        os.makedirs(banks_dir, exist_ok=True)
        filepath = os.path.join(banks_dir, file.filename)
        file.save(filepath)
        
        # Load the new bank into database
        conn = get_db()
        load_questions_to_db(conn, file.filename)
        
        
        flash(f"题库 {file.filename} 上传成功", "success")
    except Exception as e:
        flash(f"上传题库时出错: {str(e)}", "error")
    
    return redirect(url_for('banks.select_bank'))

@banks_bp.route('/delete_bank', methods=['POST'])
@admin_required
def delete_bank():
    """Route to delete a question bank."""
    bank_name = request.form.get('bank_name')
    user_id = get_user_id()
    current_bank = get_current_bank(user_id)
    
    if not bank_name:
        flash("请选择要删除的题库", "error")
        return redirect(url_for('banks.select_bank'))
    
    # Don't allow deleting the current bank
    if bank_name == current_bank:
        # Find another bank to switch to
        available_banks = get_available_banks()
        other_banks = [b for b in available_banks if b != bank_name]
        
        if other_banks:
            # Switch to another bank first
            new_bank = other_banks[0]
            set_current_bank(user_id, new_bank)
        else:
            flash("不能删除唯一的题库", "error")
            return redirect(url_for('banks.select_bank'))
    
    try:
        # Delete from database first
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM questions WHERE bank_name = ?', (bank_name,))
        
        # Also delete related history and favorites
        c.execute('''
            DELETE FROM history 
            WHERE question_id IN (
                SELECT id FROM questions WHERE bank_name = ?
            )
        ''', (bank_name,))
        
        c.execute('''
            DELETE FROM favorites 
            WHERE question_id IN (
                SELECT id FROM questions WHERE bank_name = ?
            )
        ''', (bank_name,))
        
        conn.commit()
        
        
        # Delete the file
        # 确保bank_name有.csv后缀来查找文件
        if not bank_name.endswith('.csv'):
            file_name = bank_name + '.csv'
        else:
            file_name = bank_name
            bank_name = bank_name[:-4]  # 去掉.csv后缀存储
        bank_path = os.path.join('./questions-bank', file_name)
        if os.path.exists(bank_path):
            os.remove(bank_path)
        
        flash(f"题库 {bank_name} 已删除", "success")
    except Exception as e:
        flash(f"删除题库时出错: {str(e)}", "error")
    
    return redirect(url_for('banks.select_bank'))

@banks_bp.route('/auto_load_all_banks')
@admin_required
def auto_load_all_banks():
    """自动加载所有尚未加载到数据库的题库（开发调试用）"""
    user_id = get_user_id()
    available_banks = get_available_banks()
    
    conn = get_db()
    c = conn.cursor()
    loaded_count = 0
    
    for bank in available_banks:
        # 检查是否已加载
        c.execute('SELECT COUNT(*) as count FROM questions WHERE bank_name = ?', (bank,))
        count_row = c.fetchone()
        if count_row and count_row['count'] == 0:
            # 题库未加载，加载它
            try:
                load_questions_to_db(conn, bank)
                loaded_count += 1
                print(f"自动加载题库: {bank}")
            except Exception as e:
                print(f"加载题库 {bank} 时出错: {e}")
    
    
    
    if loaded_count > 0:
        flash(f"已自动加载 {loaded_count} 个题库", "success")
    else:
        flash("所有题库均已加载", "info")
    
    return redirect(url_for('banks.select_bank'))