"""
examcat - 题目路由蓝图
"""
import os
import random
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from ..utils.auth import login_required, get_user_id
from ..utils.questions import fetch_question, random_question_id, is_favorite
from ..utils.database import get_db, get_current_bank, get_current_question_id, extract_qid_number, get_next_question_id, db_logger, get_question_count, restore_qid

questions_bp = Blueprint('questions', __name__, template_folder='../templates/base')

@questions_bp.route('/random', methods=['GET'])
@login_required
def random_question():
    """Route to get a random question."""
    user_id = get_user_id()
    current_bank = get_current_bank(user_id)
    qid = random_question_id(user_id)
    
    conn = get_db()
    c = conn.cursor()
    # Get total questions count for current bank
    c.execute('SELECT COUNT(*) as total FROM questions WHERE bank_name = ?', (current_bank,))
    total = c.fetchone()['total']
    # Get answered questions count for current bank
    c.execute('''
        SELECT COUNT(DISTINCT h.question_id) as answered 
        FROM history h 
        JOIN questions q ON h.question_id = q.id 
        WHERE h.user_id = ? AND q.bank_name = ?
    ''', (user_id, current_bank))
    answered = c.fetchone()['answered']
    
    
    if not qid:
        flash("您已完成当前题库所有题目！可以重置历史以重新开始，或切换其他题库。", "info")
        return render_template('question.html', 
                              question=None, 
                              answered=answered, 
                              total=total,
                              current_bank=current_bank)
        
    q = fetch_question(qid)
    is_fav = is_favorite(user_id, qid)
    
    return render_template('question.html', 
                          question=q, 
                          answered=answered, 
                          total=total,
                          is_favorite=is_fav,
                          current_bank=current_bank)

@questions_bp.route('/question/<qid>', methods=['GET', 'POST'])
@login_required
def show(qid):
    """Route to view and answer a specific question."""
    user_id = get_user_id()
    current_bank = get_current_bank(user_id)
    q = fetch_question(qid)
    
    if q is None:
        flash("题目不存在", "error")
        db_logger.error(f"[{os.getpid()}] questions.show: 用户{user_id}, 题目{qid}")

        return redirect(url_for('main.index'))
    
    # Calculate next question ID
    next_qid = get_next_question_id(qid, current_bank)

    # Handle form submission (answer)
    if request.method == 'POST':
        user_answer = request.form.getlist('answer')
        user_answer_str = "".join(sorted(user_answer))
        correct = int(user_answer_str == "".join(sorted(q['answer'])))

        # Save answer to history
        conn = get_db()
        c = conn.cursor()
        c.execute(
            'INSERT INTO history (user_id, question_id, user_answer, correct) VALUES (?,?,?,?)',
            (user_id, qid, user_answer_str, correct)
        )
        db_logger.info(f"[{os.getpid()}] Add history: 用户{user_id}, 题目{qid}, 答案{user_answer_str}, 正确{correct}")
        
        # Get updated stats for current bank
        c.execute('SELECT COUNT(*) AS total FROM questions WHERE bank_name = ?', (current_bank,))
        total = c.fetchone()['total']
        c.execute('''
            SELECT COUNT(DISTINCT h.question_id) AS answered 
            FROM history h 
            JOIN questions q ON h.question_id = q.id 
            WHERE h.user_id = ? AND q.bank_name = ?
        ''', (user_id, current_bank))
        answered = c.fetchone()['answered']
        
        conn.commit()       

        result_msg = "回答正确" if correct else f"回答错误，正确答案：{q['answer']}"
        flash(result_msg, "success" if correct else "error")
        
        is_fav = is_favorite(user_id, qid)
        
        return render_template('question.html',
                              question=q,
                              result_msg=result_msg,
                              answered=answered,
                              total=total,
                              next_qid=next_qid,  # 添加next_qid参数
                              is_favorite=is_fav,
                              current_bank=current_bank)

    # Handle GET request
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) AS total FROM questions WHERE bank_name = ?', (current_bank,))
    total = c.fetchone()['total']
    c.execute('''
        SELECT COUNT(DISTINCT h.question_id) AS answered 
        FROM history h 
        JOIN questions q ON h.question_id = q.id 
        WHERE h.user_id = ? AND q.bank_name = ?
    ''', (user_id, current_bank))
    answered = c.fetchone()['answered']
    
    
    is_fav = is_favorite(user_id, qid)

    return render_template('question.html',
                          question=q,
                          answered=answered,
                          total=total,
                          next_qid=next_qid,
                          is_favorite=is_fav,
                          current_bank=current_bank)

@questions_bp.route('/history')
@login_required
def show_history():
    """Route to view answer history."""
    user_id = get_user_id()
    current_bank = get_current_bank(user_id)
    
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT h.* FROM history h 
        JOIN questions q ON h.question_id = q.id 
        WHERE h.user_id = ? AND q.bank_name = ? 
        ORDER BY h.timestamp DESC
    ''', (user_id, current_bank))
    rows = c.fetchall()
    
    history_data = []
    for r in rows:
        q = fetch_question(r['question_id'])
        stem = q['stem'] if q else '题目已删除'
        history_data.append({
            'id': r['id'],
            'question_id': r['question_id'],
            'stem': stem,
            'user_answer': r['user_answer'],
            'correct': r['correct'],
            'timestamp': r['timestamp']
        })
    
    return render_template('history.html', 
                          history=history_data,
                          current_bank=current_bank)

@questions_bp.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    """Route to search for questions by keyword."""
    user_id = get_user_id()
    current_bank = get_current_bank(user_id)
    query = request.form.get('query', '')
    results = []
    
    if query:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM questions WHERE bank_name = ? AND stem LIKE ?", 
                  (current_bank, '%'+query+'%'))
        rows = c.fetchall()
        
        
        for row in rows:
            q = {
                'id': row['id'],
                'stem': row['stem']
            }
            results.append(q)
    
    return render_template('search.html', 
                          query=query, 
                          results=results,
                          current_bank=current_bank)

@questions_bp.route('/wrong')
@login_required
def wrong_questions():
    """Route to view wrong answers."""
    user_id = get_user_id()
    current_bank = get_current_bank(user_id)
    
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT h.question_id FROM history h 
        JOIN questions q ON h.question_id = q.id 
        WHERE h.user_id = ? AND h.correct = 0 AND q.bank_name = ?
    ''', (user_id, current_bank))
    rows = c.fetchall()
    
    # 获取错题ID集合（去重）
    wrong_ids = set(r['question_id'] for r in rows)
    questions_list = []
    
    # 首先获取所有错题信息
    for qid in wrong_ids:
        q = fetch_question(qid)
        if q:
            questions_list.append(q)
    
    # 按照数字ID从小到大排序
    # 使用 extract_qid_number 函数提取数字ID进行排序
    questions_list.sort(key=lambda x: extract_qid_number(x['id']))
    
    return render_template('wrong.html', 
                          questions=questions_list,
                          current_bank=current_bank)

@questions_bp.route('/wrong_start')
@login_required
def wrong_start():
    """Route to start practicing wrong questions in sequential mode."""
    user_id = get_user_id()
    current_bank = get_current_bank(user_id)
    
    conn = get_db()
    c = conn.cursor()
    
    # Get wrong questions for current bank
    c.execute('''
        SELECT DISTINCT h.question_id 
        FROM history h 
        JOIN questions q ON h.question_id = q.id 
        WHERE h.user_id = ? AND h.correct = 0 AND q.bank_name = ?
    ''', (user_id, current_bank))
    rows = c.fetchall()
    
    if not rows:
        flash("当前题库没有错题或还未答题", "info")
        return redirect(url_for('main.index'))
    
    # Extract question IDs
    wrong_ids = [row['question_id'] for row in rows]
    
    # Sort by numeric ID using extract_qid_number
    wrong_ids.sort(key=extract_qid_number)
    
    # Get the first wrong question
    first_qid = wrong_ids[0]
    
    return redirect(url_for('questions.show_wrong_question', qid=first_qid))

@questions_bp.route('/only_wrong/<qid>', methods=['GET', 'POST'])
@login_required
def show_wrong_question(qid):
    """Route to show and handle wrong questions in sequential mode."""
    user_id = get_user_id()
    current_bank = get_current_bank(user_id)
    q = fetch_question(qid)
    
    if q is None:
        flash("题目不存在", "error")
        db_logger.error(f"[{os.getpid()}] questions.show_wrong_question: 用户{user_id}, 题目{qid}")
        return redirect(url_for('main.index'))
    
    # Verify the question belongs to current bank
    if q.get('bank_name') != current_bank:
        flash("题目不属于当前题库", "error")
        return redirect(url_for('questions.wrong_start'))
    
    next_qid = None
    result_msg = None
    user_answer_str = ""
    
    conn = get_db()
    c = conn.cursor()
    
    # Handle POST request (user submitted an answer)
    if request.method == 'POST':
        user_answer = request.form.getlist('answer')
        user_answer_str = "".join(sorted(user_answer))
        correct = int(user_answer_str == "".join(sorted(q['answer'])))
        
        # Save answer to history
        c.execute('INSERT INTO history (user_id, question_id, user_answer, correct) '
                  'VALUES (?,?,?,?)',
                  (user_id, qid, user_answer_str, correct))
        db_logger.info(f"[{os.getpid()}] Add history: 用户{user_id}, 题目{qid}, 答案{user_answer_str}, 正确{correct}")
        
        # If answered correctly, remove from wrong questions list for next navigation
        conn.commit()
        
        result_msg = "回答正确！" if correct else f"回答错误，正确答案：{q['answer']}"
        flash(result_msg, "success" if correct else "error")
    
    # Get wrong questions list for current bank (after possible update from POST)
    c.execute('''
        SELECT DISTINCT h.question_id 
        FROM history h 
        JOIN questions q ON h.question_id = q.id 
        WHERE h.user_id = ? AND h.correct = 0 AND q.bank_name = ?
    ''', (user_id, current_bank))
    rows = c.fetchall()
    
    wrong_ids = [row['question_id'] for row in rows]
    
    if not wrong_ids:
        flash("恭喜！您已经做完了所有错题。", "success")
        return redirect(url_for('main.index'))
    
    # Sort wrong question IDs by numeric ID
    wrong_ids.sort(key=extract_qid_number)
    
    # Find next wrong question
    try:
        current_index = wrong_ids.index(qid)
        if current_index + 1 < len(wrong_ids):
            next_qid = wrong_ids[current_index + 1]
        else:
            # If this is the last wrong question, loop back to first
            next_qid = wrong_ids[0]
    except ValueError:
        # Current question is no longer in wrong list (answered correctly), go to first
        next_qid = wrong_ids[0] if wrong_ids else None
    
    # Get progress statistics for wrong questions
    total_wrong = len(wrong_ids)
    # Current position in wrong questions list
    try:
        current_position = wrong_ids.index(qid) + 1
    except ValueError:
        current_position = 1
    
    # Get total questions and answered questions count for current bank
    c.execute('SELECT COUNT(*) AS total FROM questions WHERE bank_name = ?', (current_bank,))
    total = c.fetchone()['total']
    
    c.execute('''
        SELECT COUNT(DISTINCT h.question_id) AS answered 
        FROM history h 
        JOIN questions q ON h.question_id = q.id 
        WHERE h.user_id = ? AND q.bank_name = ?
    ''', (user_id, current_bank))
    answered = c.fetchone()['answered']
    
    is_fav = is_favorite(user_id, qid)
    
    return render_template('question.html',
                          question=q,
                          result_msg=result_msg,
                          next_qid=next_qid,
                          wrong_mode=True,  # New flag to indicate wrong question mode
                          user_answer=user_answer_str,
                          answered=current_position,
                          total=total_wrong,
                          wrong_progress=f"{current_position}/{total_wrong}",  # Progress for wrong questions
                          is_favorite=is_fav,
                          current_bank=current_bank)

@questions_bp.route('/sequential_start')
@login_required
def sequential_start():
    """Route to start or continue sequential answering mode."""
    user_id = get_user_id()
    
    # Use get_current_question_id to ensure the question belongs to current bank
    current_qid = get_current_question_id(user_id)
    
    if current_qid is None:
        flash("当前题库中没有题目或无法获取题目！", "error")
        return redirect(url_for('main.index'))
    
    return redirect(url_for('questions.show_sequential_question', qid=current_qid))

@questions_bp.route('/sequential/<qid>', methods=['GET', 'POST'])
@login_required
def show_sequential_question(qid):
    """Route to show and handle sequential questions."""
    user_id = get_user_id()
    current_bank = get_current_bank(user_id)
    q = fetch_question(qid)
    
    if q is None:
        conn = get_db()
        c = conn.cursor()
        
        # 获取题库总题数
        total = get_question_count(conn, current_bank)        
        # 提取当前题目ID的数字部分
        current_number = extract_qid_number(qid)        
        # 判断是否为数字ID超过总题数的情况
        if current_number and current_number > total:
            # 设置为第一题
            next_qid = restore_qid(current_bank)
            # Update current_seq_qid to the current question
            c.execute('UPDATE users SET current_seq_qid = ? WHERE id = ?', (next_qid, user_id))
            conn.commit()
            # 获取进度统计
            c.execute('SELECT COUNT(*) AS total FROM questions WHERE bank_name = ?', (current_bank,))
            total = c.fetchone()['total']
            c.execute('''
                SELECT COUNT(DISTINCT h.question_id) AS answered 
                FROM history h 
                JOIN questions q ON h.question_id = q.id 
                WHERE h.user_id = ? AND q.bank_name = ?
            ''', (user_id, current_bank))
            answered = c.fetchone()['answered']
            
            return render_template('question.html',
                                  question=None,
                                  next_qid=next_qid,
                                  sequential_mode=True,
                                  answered=answered,
                                  total=total,
                                  current_bank=current_bank)
        else:
            # 其他错误情况
            flash("题目不存在", "error")
            db_logger.error(f"[{os.getpid()}] questions.show_sq: 用户{user_id}, 题目{qid}")
            return redirect(url_for('main.index'))

    # Verify the question belongs to current bank
    if q.get('bank_name') != current_bank:
        # If not, get the correct question for current bank
        correct_qid = get_current_question_id(user_id)
        if correct_qid:
            flash("已切换到当前题库的正确题目位置", "info")
            return redirect(url_for('questions.show_sequential_question', qid=correct_qid))
        else:
            flash("当前题库中没有题目", "error")
            return redirect(url_for('main.index'))

    next_qid = None
    result_msg = None
    user_answer_str = ""
    
    conn = get_db()
    c = conn.cursor()
    
    # Update current_seq_qid to the current question
    c.execute('UPDATE users SET current_seq_qid = ? WHERE id = ?', (qid, user_id))
    conn.commit()
    
    # Handle POST request (user submitted an answer)
    if request.method == 'POST':
        user_answer = request.form.getlist('answer')
        user_answer_str = "".join(sorted(user_answer))
        correct = int(user_answer_str == "".join(sorted(q['answer'])))
        
        # Save answer to history
        c.execute('INSERT INTO history (user_id, question_id, user_answer, correct, bank_name) '
                  'VALUES (?,?,?,?,?)',
                  (user_id, qid, user_answer_str, correct, current_bank))
        db_logger.info(f"[{os.getpid()}] Add history: 用户{user_id}, 题目{qid}, 答案{user_answer_str}, 正确{correct}")
        
        next_qid = get_next_question_id(qid, current_bank)
        
        if next_qid:
            # 更新current_seq_qid为下一题
            c.execute('UPDATE users SET current_seq_qid = ? WHERE id = ?',
                      (next_qid, user_id))
        else:
            # 没有找到下一题，清空current_seq_qid
            c.execute('UPDATE users SET current_seq_qid = NULL WHERE id = ?',
                      (user_id,))
            flash("当前题库没有更多题目", "info")
        
        result_msg = "回答正确！" if correct else f"回答错误，正确答案：{q['answer']}"
        flash(result_msg, "success" if correct else "error")
        conn.commit()
    
    # 在GET请求时也计算下一题ID（用于显示"下一题"链接）
    if request.method == 'GET':
        
        # 获取当前题库所有题目
        c.execute('SELECT id FROM questions WHERE bank_name = ?', (current_bank,))
        all_questions = [row['id'] for row in c.fetchall()]
        
        if all_questions:
            # 按数字部分排序
            all_questions.sort(key=extract_qid_number)
            
            # 找到当前题目在列表中的位置
            try:
                current_index = all_questions.index(qid)
                # 计算下一个题目的索引
                if current_index + 1 < len(all_questions):
                    next_qid = all_questions[current_index + 1]
                else:
                    # 已经是最后一题，循环到第一题
                    next_qid = all_questions[0]
            except ValueError:
                # 当前题目不在列表中（不应该发生），返回第一个题目
                next_qid = all_questions[0]
    
    # Get progress statistics for current bank
    c.execute('SELECT COUNT(*) AS total FROM questions WHERE bank_name = ?', (current_bank,))
    total = c.fetchone()['total']
    
    c.execute('''
        SELECT COUNT(DISTINCT h.question_id) AS answered 
        FROM history h 
        JOIN questions q ON h.question_id = q.id 
        WHERE h.user_id = ? AND q.bank_name = ?
    ''', (user_id, current_bank))
    answered = c.fetchone()['answered']
    
    
    
    is_fav = is_favorite(user_id, qid)
    
    return render_template('question.html',
                          question=q,
                          result_msg=result_msg,
                          next_qid=next_qid,
                          sequential_mode=True,
                          user_answer=user_answer_str,
                          answered=answered,
                          total=total,
                          is_favorite=is_fav,
                          current_bank=current_bank)