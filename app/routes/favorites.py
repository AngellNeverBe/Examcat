"""
examcat - 收藏路由蓝图
"""
import os
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from ..utils.auth import login_required, get_user_id
from ..utils.database import get_db, db_logger
from ..utils.questions import fetch_question
from ..utils.banks import get_current_bank_id

favorites_bp = Blueprint('favorites', __name__, url_prefix='/favorites', template_folder='../templates/base')

@favorites_bp.route('/')
@login_required
def show():
    """显示收藏列表"""
    user_id = get_user_id()
    # 获取当前题库ID
    current_bank_id = get_current_bank_id(user_id)[0]
    
    if not current_bank_id:
        flash("请先选择题库", "error")
        return redirect(url_for('main.index'))
    
    conn = get_db()
    c = conn.cursor()
    
    # 获取收藏的题目（连接questions和banks表）
    c.execute('''
        SELECT 
            f.question_id, 
            f.tag, 
            f.bank_id,
            q.stem, 
            q.answer, 
            q.type, 
            q.category,
            b.bankname
        FROM favorites f 
        JOIN questions q ON f.question_id = q.id 
        JOIN banks b ON f.bank_id = b.id
        WHERE f.user_id = ? AND f.bank_id = ?
        ORDER BY f.created_at DESC
    ''', (user_id, current_bank_id))
    
    rows = c.fetchall()
    favorites_data = []
    
    for r in rows:
        # 获取题目详细信息
        q = fetch_question(r['question_id'])
        if q:
            favorites_data.append({
                'question_id': r['question_id'],
                'tag': r['tag'] or '未标记',
                'stem': r['stem'][:100] + '...' if len(r['stem']) > 100 else r['stem'],
                'answer': r['answer'],
                'type': r['type'],
                'type2': r['type2'],
                'category': r['category'],
                'bank_id': r['bank_id'],
                'bankname': r['bankname']
            })
    
    return render_template('favorites.html', 
                          favorites=favorites_data,
                          current_bank_id=current_bank_id)

@favorites_bp.route('/<int:qid>', methods=['POST'])
@login_required
def add(qid):
    """添加收藏"""
    user_id = get_user_id()
    
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
              request.headers.get('X-Ajax-Navigation') == 'true'

    conn = get_db()
    c = conn.cursor()
    
    try:
        # 检查题目是否存在，并获取bank_id
        c.execute('''
            SELECT q.id, q.bank_id, b.bankname
            FROM questions q
            JOIN banks b ON q.bank_id = b.id
            WHERE q.id = ?
        ''', (qid,))
        
        question_row = c.fetchone()
        if not question_row:
            if is_ajax:
                return jsonify(success=False, error="题目不存在")
            
            flash("题目不存在", "error")
            db_logger.error(f"[{os.getpid()}] favorites.add: 用户{user_id}, 题目{qid}")
            return redirect(request.referrer or url_for('main.index'))
        
        bank_id = question_row['bank_id']
        
        # 检查是否已经收藏
        c.execute('SELECT 1 FROM favorites WHERE user_id = ? AND question_id = ?', (user_id, qid))
        if c.fetchone():
            if is_ajax:
                return jsonify(success=True, msg="已经收藏过了")
            
            flash("已经收藏过了", "info")
        else:
            # 添加收藏
            c.execute('''
                INSERT INTO favorites (user_id, question_id, bank_id, tag) 
                VALUES (?, ?, ?, ?)
            ''', (user_id, qid, bank_id, ''))
            
            db_logger.info(f"[{os.getpid()}] Add favorites: 用户{user_id}, 题目{qid}, 题库{question_row['bankname']}")
            conn.commit()
            
            if is_ajax:
                return jsonify(success=True, msg="收藏成功！")
            
            flash("收藏成功！", "success")
        
    except Exception as e:
        if is_ajax:
            return jsonify(success=False, error=f"收藏失败: {str(e)}")
        
        flash(f"收藏失败: {str(e)}", "error")
        db_logger.error(f"[{os.getpid()}] favorites.add: 用户{user_id}, 题目{qid}, 错误{e}")
    
    # 重定向回原页面
    referrer = request.referrer
    if referrer:
        return redirect(referrer)
    return redirect(url_for('questions.show', qid=qid))

@favorites_bp.route('/<int:qid>', methods=['DELETE'])
@login_required
def remove(qid):
    """移除收藏"""
    user_id = get_user_id()
    
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
            request.headers.get('X-Ajax-Navigation') == 'true'


    conn = get_db()
    c = conn.cursor()
    
    try:        
        # 删除收藏
        c.execute('DELETE FROM favorites WHERE user_id = ? AND question_id = ?', 
                  (user_id, qid))
        
        db_logger.info(f"[{os.getpid()}] Remove favorites: 用户{user_id}, 题目{qid}")
        conn.commit()
        
        if is_ajax:
            return jsonify(success=True, msg="已取消收藏")
        
        flash("已取消收藏", "success")
        
    except Exception as e:
        if is_ajax:
            return jsonify(success=False, error=f"取消收藏失败: {str(e)}")
        
        flash(f"取消收藏失败: {str(e)}", "error")
        db_logger.error(f"[{os.getpid()}] favorites.remove: 用户{user_id}, 题目{qid}, 错误{e}")        
    
    # 重定向回原页面
    referrer = request.referrer
    if referrer:
        return redirect(referrer)
    return redirect(url_for('questions.show', qid=qid))

@favorites_bp.route('/<int:qid>/tag', methods=['POST'])
@login_required
def update_tag(qid):
    """更新收藏标签"""    
    user_id = get_user_id()
    new_tag = request.form.get('tag', '')
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute('''
            UPDATE favorites 
            SET tag = ? 
            WHERE user_id = ? AND question_id = ?
        ''', (new_tag, user_id, qid))
        
        conn.commit()
        return jsonify({"success": True, "msg": "标记更新成功"})
    except Exception as e:
        return jsonify({"success": False, "msg": f"更新失败: {str(e)}"}), 500

@favorites_bp.route('/tags/<tag>')
@login_required
def by_tag(tag):
    """按标签查看收藏"""
    user_id = get_user_id()
    # 获取当前题库ID
    current_bank_id = get_current_bank_id(user_id)[0]
    
    if not current_bank_id:
        flash("请先选择题库", "error")
        return redirect(url_for('main.index'))
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT 
            f.question_id, 
            q.stem, 
            q.answer, 
            q.type,
            b.bankname
        FROM favorites f 
        JOIN questions q ON f.question_id = q.id 
        JOIN banks b ON f.bank_id = b.id
        WHERE f.user_id = ? AND f.tag = ? AND f.bank_id = ?
        ORDER BY f.created_at DESC
    ''', (user_id, tag, current_bank_id))
    
    rows = c.fetchall()
    favorites_data = []
    
    for r in rows:
        favorites_data.append({
            'question_id': r['question_id'],
            'stem': r['stem'][:100] + '...' if len(r['stem']) > 100 else r['stem'],
            'answer': r['answer'],
            'type': r['type'],
            'bankname': r['bankname']
        })
    
    return render_template('favorites_by_tag.html',
                          tag=tag,
                          favorites=favorites_data,
                          current_bank_id=current_bank_id)

@favorites_bp.route('/tags')
@login_required
def tag_list():
    """显示所有标签"""
    user_id = get_user_id()
    # 获取当前题库ID
    current_bank_id = get_current_bank_id(user_id)[0]
    
    if not current_bank_id:
        flash("请先选择题库", "error")
        return redirect(url_for('main.index'))
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT 
            f.tag, 
            COUNT(*) as count,
            b.bankname
        FROM favorites f 
        JOIN banks b ON f.bank_id = b.id
        WHERE f.user_id = ? AND f.bank_id = ? 
          AND f.tag IS NOT NULL AND f.tag != ''
        GROUP BY f.tag
        ORDER BY count DESC
    ''', (user_id, current_bank_id))
    
    tags = []
    for r in c.fetchall():
        tags.append({
            'tag': r['tag'],
            'count': r['count'],
            'bankname': r['bankname']
        })    
    
    return render_template('tag_list.html',
                          tags=tags,
                          current_bank_id=current_bank_id)
