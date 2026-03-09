"""
examcat - 收藏路由蓝图
"""
import os
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from ..utils.auth import login_required, get_user_id, is_logged_in
from ..utils.database import get_db, get_current_bank, db_logger
from ..utils.questions import fetch_question, is_favorite

favorites_bp = Blueprint('favorites', __name__, url_prefix='/favorites', template_folder='../templates/base')

@favorites_bp.route('/')
@login_required
def show():
    """显示收藏列表"""
    user_id = get_user_id()
    current_bank = get_current_bank(user_id)
    
    conn = get_db()
    c = conn.cursor()
    
    # 获取收藏的题目
    c.execute('''
        SELECT f.question_id, f.tag, q.stem, q.answer, q.difficulty, q.qtype, q.category
        FROM favorites f 
        JOIN questions q ON f.question_id=q.id 
        WHERE f.user_id=? AND q.bank_name = ?
        ORDER BY f.created_at DESC
    ''', (user_id, current_bank))
    
    rows = c.fetchall()
    favorites_data = []
    
    for r in rows:
        q = fetch_question(r['question_id'])
        if q:
            favorites_data.append({
                'question_id': r['question_id'],
                'tag': r['tag'] or '未标记',
                'stem': r['stem'][:100] + '...' if len(r['stem']) > 100 else r['stem'],
                'answer': r['answer'],
                'difficulty': r['difficulty'],
                'type': r['qtype'],
                'category': r['category']
            })
    
    
    
    return render_template('favorites.html', 
                          favorites=favorites_data,
                          current_bank=current_bank)

@favorites_bp.route('/add/<qid>', methods=['POST'])
@login_required
def add(qid):
    """添加收藏"""
    user_id = get_user_id()
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        # 检查题目是否存在
        c.execute('SELECT id FROM questions WHERE id = ?', (qid,))
        if not c.fetchone():
            flash("题目不存在", "error")
            db_logger.error(f"[{os.getpid()}] favorites.add: 用户{user_id}, 题目{qid}")

            return redirect(request.referrer or url_for('main.index'))
        
        # 添加收藏
        c.execute('INSERT OR IGNORE INTO favorites (user_id, question_id, tag) VALUES (?,?,?)',
                  (user_id, qid, ''))
        db_logger.info(f"[{os.getpid()}] Add favorites: 用户{user_id}, 题目{qid}")

        conn.commit()
        flash("收藏成功！", "success")
    except Exception as e:
        flash(f"收藏失败: {str(e)}", "error")
        db_logger.error(f"[{os.getpid()}] favorites.add: 用户{user_id}, 题目{qid}, 错误{e}")
    
    # 重定向回原页面
    referrer = request.referrer
    if referrer:
        return redirect(referrer)
    return redirect(url_for('questions.show', qid=qid))

@favorites_bp.route('/remove/<qid>', methods=['POST'])
@login_required
def remove(qid):
    """移除收藏"""
    user_id = get_user_id()
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute('DELETE FROM favorites WHERE user_id=? AND question_id=?', 
                  (user_id, qid))
        db_logger.info(f"[{os.getpid()}] Remove favorites: 用户{user_id}, 题目{qid}")

        conn.commit()
        flash("已取消收藏", "success")
    except Exception as e:
        flash(f"取消收藏失败: {str(e)}", "error")
        db_logger.error(f"[{os.getpid()}] favorites.remove: 用户{user_id}, 题目{qid}, 错误{e}")        
    
    # 重定向回原页面
    referrer = request.referrer
    if referrer:
        return redirect(referrer)
    return redirect(url_for('questions.show', qid=qid))

@favorites_bp.route('/tag/<qid>', methods=['POST'])
@login_required
def update_tag(qid):
    """更新收藏标签"""
    if not is_logged_in():
        return jsonify({"success": False, "msg": "未登录"}), 401
    
    user_id = get_user_id()
    new_tag = request.form.get('tag', '')
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute('UPDATE favorites SET tag=? WHERE user_id=? AND question_id=?',
                  (new_tag, user_id, qid))
        conn.commit()
        return jsonify({"success": True, "msg": "标记更新成功"})
    except Exception as e:
        return jsonify({"success": False, "msg": f"更新失败: {str(e)}"}), 500

@favorites_bp.route('/by_tag/<tag>')
@login_required
def by_tag(tag):
    """按标签查看收藏"""
    user_id = get_user_id()
    current_bank = get_current_bank(user_id)
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT f.question_id, q.stem, q.answer, q.difficulty, q.qtype
        FROM favorites f 
        JOIN questions q ON f.question_id=q.id 
        WHERE f.user_id=? AND f.tag=? AND q.bank_name = ?
        ORDER BY f.created_at DESC
    ''', (user_id, tag, current_bank))
    
    rows = c.fetchall()
    favorites_data = []
    
    for r in rows:
        favorites_data.append({
            'question_id': r['question_id'],
            'stem': r['stem'][:100] + '...' if len(r['stem']) > 100 else r['stem'],
            'answer': r['answer'],
            'difficulty': r['difficulty'],
            'type': r['qtype']
        })
    
    return render_template('favorites_by_tag.html',
                          tag=tag,
                          favorites=favorites_data,
                          current_bank=current_bank)

@favorites_bp.route('/tags')
@login_required
def tag_list():
    """显示所有标签"""
    user_id = get_user_id()
    current_bank = get_current_bank(user_id)
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT f.tag, COUNT(*) as count
        FROM favorites f 
        JOIN questions q ON f.question_id=q.id 
        WHERE f.user_id=? AND q.bank_name = ? AND f.tag IS NOT NULL AND f.tag != ''
        GROUP BY f.tag
        ORDER BY count DESC
    ''', (user_id, current_bank))
    
    tags = []
    for r in c.fetchall():
        tags.append({
            'tag': r['tag'],
            'count': r['count']
        })
    
    
    
    return render_template('tag_list.html',
                          tags=tags,
                          current_bank=current_bank)