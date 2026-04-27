"""
examcat - 认证辅助函数
"""
from typing import Tuple, Dict, List, Any, Optional
from functools import wraps
from flask import session, request, redirect, url_for, flash
from werkzeug.security import check_password_hash
from .database import get_db

# 管理员账号配置（密码使用 generate_password_hash 生成）
ADMIN_CREDENTIALS = {
    'admin':'pbkdf2:sha256:600000$JFYTJtNYkvSIlL2z$37f83bc130fb93a5523cee128e934c0bdfb86cffb53eec4e8500b7e3aee8e0a4'
}

# ======== 核心操作 ========
def login_required(f):
    """装饰器：要求登录"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not _is_logged_in():
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """装饰器：要求管理员权限"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not _is_admin():
            flash("需要管理员权限才能访问此页面", "error")
            if _is_logged_in():
                return redirect(url_for('main.index'))
            else:
                return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def _is_logged_in():
    """检查用户是否登录"""
    return 'user_id' in session

def _is_admin():
    """检查当前用户是否为管理员"""
    return session.get('is_admin', False)

def get_user_id() -> int:
    """获取当前用户ID"""
    return session.get('user_id')

def validate_username(username: str) -> Tuple[bool, str]:
    """
    验证用户名是否有效

    Args:
        username: 用户名

    Returns:
        (是否有效, 错误信息)
    """
    # 检查是否尝试注册管理员账号
    if not username:
        return False, "用户名不能为空"

    if username == 'admin':
        return False, "不能注册管理员账号"

    if len(username) < 3:
        return False, "用户名长度过短"

    if len(username) >30:
        return False, "用户名长度过长"

    from .database import get_db
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id FROM users WHERE username=?', (username,))
    if c.fetchone():
        return False, "用户名已存在，请更换用户名"

    return True, "用户名有效"

def validate_username_update(username: str, exclude_user_id: int) -> Tuple[bool, str]:
    """
    验证修改用户名是否有效（排除当前用户自己）

    Args:
        username: 新用户名
        exclude_user_id: 要排除的用户ID（当前用户）

    Returns:
        (是否有效, 错误信息)
    """
    if not username:
        return False, "用户名不能为空"

    if len(username) < 3:
        return False, "用户名长度过短"

    if len(username) > 30:
        return False, "用户名长度过长"

    from .database import get_db
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id FROM users WHERE username=? AND id != ?', (username, exclude_user_id))
    if c.fetchone():
        return False, "用户名已存在，请更换用户名"

    return True, "用户名有效"

def validate_email(email: str) -> Tuple[bool, str]:
    """
    验证邮箱地址是否有效。
    
    Args:
        email: 邮箱地址
    
    Returns:
        (是否有效, 错误信息)
    """
    if not email:
        return False, "邮箱地址不能为空"
    
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        return False, "邮箱地址格式无效"
    
    return True, "邮箱地址有效"

def validate_passward(password: str, confirm_password: str) -> Tuple[bool, str]:
    """
    验证密码是否有效
    
    Args:
        password: 密码
        confirm_password: 确认密码
    
    Returns:
        (是否有效, 错误信息)
    """
    if not password:
        return False, "密码不能为空"
        
    if password != confirm_password:
        return False, "两次输入的密码不一致"
        
    if len(password) < 6:
        return False, "密码长度不能少于6个字符"
    
    return True, "密码有效"

def verify_admin_credentials(username, password):
    """验证管理员账号密码"""
    if username in ADMIN_CREDENTIALS:
        admin_passwd_hash = ADMIN_CREDENTIALS[username]
        if check_password_hash(admin_passwd_hash, password):
            return True
    return None

# ======== 数据相关 ========
def fetch_user_question_stats(user_id: int, bank_id: int) -> Dict[str, Any]:
    """
    获取用户在指定题库下的答题统计（全题库）

    Args:
        user_id (int): 用户ID
        bank_id (int): 题库ID

    Returns:
        dict: 统计字典，包含以下字段：
            - answered: 已答题目数 (complete=1)
            - correct: 答对题目数 (correct=1)
            - wrong: 答错题目数 (correct=0)
            - total: 题库总题目数 (从banks表获取)
            - answered_percentage: 已答题目百分比
            - correct_percentage: 正确题目百分比（基于已答题目）
            - wrong_percentage: 错误题目百分比（基于已答题目）
            - correct_total_percentage: 正确题目百分比（基于总题目数）
            - wrong_total_percentage: 错误题目百分比（基于总题目数）
            - unanswered: 未答题目数
            - unanswered_percentage: 未答题目百分比
    """
    conn = get_db()
    c = conn.cursor()

    # 获取题库总题目数
    c.execute('SELECT total_count FROM banks WHERE id = ?', (bank_id,))
    bank_row = c.fetchone()
    total = bank_row['total_count'] if bank_row and bank_row['total_count'] else 0

    # 获取用户答题统计（使用correct_count和wrong_count字段累加）
    c.execute('''
        SELECT
            COUNT(*) as answered,
            COUNT(CASE WHEN correct = 1 THEN 1 END) as correct,
            COUNT(CASE WHEN correct = 0 THEN 1 END) as wrong,
            SUM(correct_count) as correct_count,
            SUM(wrong_count) as wrong_count
        FROM history
        WHERE user_id = ? AND bank_id = ? AND complete = 1
    ''', (user_id, bank_id))

    row = c.fetchone()
    answered = row['answered'] if row and row['answered'] else 0
    correct = row['correct'] if row and row['correct'] else 0
    wrong = row['wrong'] if row and row['wrong'] else 0
    correct_count = row['correct_count'] if row and row['correct_count'] else 0
    wrong_count = row['wrong_count'] if row and row['wrong_count'] else 0

    # 计算衍生统计
    unanswered = total - answered if total >= answered else 0

    # 计算百分比
    answered_percentage = round((answered / total * 100), 2) if total > 0 else 0
    
    # 正确率和错误率基于总尝试次数（correct + wrong）
    total_attempts = correct + wrong
    correct_percentage = round((correct / total_attempts * 100), 2) if total_attempts > 0 else 0
    wrong_percentage = round((wrong / total_attempts * 100), 2) if total_attempts > 0 else 0
    
    # 正确/错误次数与题目总数的比例
    correct_total_percentage = round((correct / total * 100), 2) if total > 0 else 0
    wrong_total_percentage = round((wrong / total * 100), 2) if total > 0 else 0
    unanswered_percentage = round((unanswered / total * 100), 2) if total > 0 else 0

    return {
        'answered': answered,
        'correct': correct,
        'wrong': wrong,
        'correct_count': correct_count,
        'wrong_count': wrong_count,
        'total': total,
        'answered_percentage': answered_percentage,
        'correct_percentage': correct_percentage,
        'wrong_percentage': wrong_percentage,
        'correct_total_percentage': correct_total_percentage,
        'wrong_total_percentage': wrong_total_percentage,
        'unanswered': unanswered,
        'unanswered_percentage': unanswered_percentage
    }

def fetch_user_question_stats_by_category(user_id: int, bank_id: int, category: str) -> Dict[str, Any]:
    """
    获取用户在指定题库下特定分类的答题统计

    Args:
        user_id (int): 用户ID
        bank_id (int): 题库ID
        category (str): 题目分类

    Returns:
        dict: 统计字典，包含以下字段：
            - answered: 已答题目数 (complete=1)
            - correct: 答对题目数 (correct=1)
            - wrong: 答错题目数 (correct=0)
            - total: 该分类总题目数 (从questions表统计)
            - answered_percentage: 已答题目百分比
            - correct_percentage: 正确题目百分比（基于已答题目）
            - wrong_percentage: 错误题目百分比（基于已答题目）
            - correct_total_percentage: 正确题目百分比（基于总题目数）
            - wrong_total_percentage: 错误题目百分比（基于总题目数）
            - unanswered: 未答题目数
            - unanswered_percentage: 未答题目百分比
    """
    conn = get_db()
    c = conn.cursor()

    # 获取该分类总题目数
    c.execute('''
        SELECT COUNT(*) as total
        FROM questions
        WHERE bank_id = ? AND category = ?
    ''', (bank_id, category))
    total_row = c.fetchone()
    total = total_row['total'] if total_row and total_row['total'] else 0

    # 获取用户答题统计（关联history和questions表以过滤分类，区分题目数目和答题次数）
    c.execute('''
        SELECT
            COUNT(*) as answered,
            COUNT(CASE WHEN h.correct = 1 THEN 1 END) as correct,
            COUNT(CASE WHEN h.correct = 0 THEN 1 END) as wrong,
            SUM(h.correct_count) as correct_count,
            SUM(h.wrong_count) as wrong_count
        FROM history h
        JOIN questions q ON h.question_id = q.id
        WHERE h.user_id = ? AND h.bank_id = ? AND h.complete = 1
          AND q.category = ?
    ''', (user_id, bank_id, category))

    row = c.fetchone()
    answered = row['answered'] if row and row['answered'] else 0
    correct = row['correct'] if row and row['correct'] else 0
    wrong = row['wrong'] if row and row['wrong'] else 0
    correct_count = row['correct_count'] if row and row['correct_count'] else 0
    wrong_count = row['wrong_count'] if row and row['wrong_count'] else 0

    # 计算衍生统计
    unanswered = total - answered if total >= answered else 0

    # 计算百分比
    answered_percentage = round((answered / total * 100), 2) if total > 0 else 0
    
    # 正确率和错误率基于总尝试次数（correct + wrong）
    total_attempts = correct + wrong
    correct_percentage = round((correct / total_attempts * 100), 2) if total_attempts > 0 else 0
    wrong_percentage = round((wrong / total_attempts * 100), 2) if total_attempts > 0 else 0
    
    # 正确/错误次数与题目总数的比例
    correct_total_percentage = round((correct / total * 100), 2) if total > 0 else 0
    wrong_total_percentage = round((wrong / total * 100), 2) if total > 0 else 0
    unanswered_percentage = round((unanswered / total * 100), 2) if total > 0 else 0

    return {
        'answered': answered,
        'correct': correct,
        'wrong': wrong,
        'correct_count': correct_count,
        'wrong_count': wrong_count,
        'total': total,
        'answered_percentage': answered_percentage,
        'correct_percentage': correct_percentage,
        'wrong_percentage': wrong_percentage,
        'correct_total_percentage': correct_total_percentage,
        'wrong_total_percentage': wrong_total_percentage,
        'unanswered': unanswered,
        'unanswered_percentage': unanswered_percentage
    }

def get_user_overall_stats(user_id: int) -> Dict[str, Any]:
    """
    获取用户在所有题库下的总体答题统计
    
    Args:
        user_id (int): 用户ID
        
    Returns:
        dict: 包含以下字段的字典：
            - total: 总答题记录数 (complete=1的记录数)
            - correct: 正确题目数 (correct=1的记录数)
            - wrong: 错误题目数 (correct=0的记录数)
            - correct_count: 总正确次数 (correct_count字段累加)
            - wrong_count: 总错误次数 (wrong_count字段累加)
            - overall_accuracy: 总体正确率百分比 (基于正确题目数量和总答题题目数量)
    """
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN correct = 1 THEN 1 END) as correct,
            COUNT(CASE WHEN correct = 0 THEN 1 END) as wrong,
            SUM(correct_count) as correct_count,
            SUM(wrong_count) as wrong_count
        FROM history
        WHERE user_id = ?
    ''', (user_id,))

    row = c.fetchone()
    total = row['total'] if row and row['total'] else 0
    correct = row['correct'] if row and row['correct'] else 0
    wrong = row['wrong'] if row and row['wrong'] else 0
    correct_count = row['correct_count'] if row and row['correct_count'] else 0
    wrong_count = row['wrong_count'] if row and row['wrong_count'] else 0
    
    # 计算总体正确率（基于正确题目数量和总答题题目数量）
    overall_accuracy = (correct / total * 100) if total > 0 else 0

    return {
        'total': total,
        'correct': correct,
        'wrong': wrong,
        'correct_count': correct_count,
        'wrong_count': wrong_count,
        'overall_accuracy': overall_accuracy
    }

def get_user_type_stats(user_id: int) -> List[Dict[str, Any]]:
    """
    获取用户在所有题库下的题型统计
    
    Args:
        user_id (int): 用户ID
        
    Returns:
        list[dict]: 每个题型统计字典，包含字段：
            - type: 题型名称
            - total: 该题型总答题数
            - correct: 该题型正确题目数
            - wrong: 该题型错误题目数
            - correct_count: 该题型总正确次数
            - wrong_count: 该题型总错误次数
            - accuracy: 该题型正确率百分比 (基于正确题目数量和总答题题目数量)
    """
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT
            q.type,
            COUNT(*) as total,
            COUNT(CASE WHEN h.correct = 1 THEN 1 END) as correct,
            COUNT(CASE WHEN h.correct = 0 THEN 1 END) as wrong,
            SUM(h.correct_count) as correct_count,
            SUM(h.wrong_count) as wrong_count
        FROM history h
        JOIN questions q ON h.question_id = q.id
        WHERE h.user_id = ?
        GROUP BY q.type
    ''', (user_id,))
    
    type_stats = []
    for r in c.fetchall():
        correct = r['correct'] if r['correct'] else 0
        wrong = r['wrong'] if r['wrong'] else 0
        correct_count = r['correct_count'] if r['correct_count'] else 0
        wrong_count = r['wrong_count'] if r['wrong_count'] else 0

        type_stats.append({
            'type': r['type'] or '未分类',
            'total': r['total'],
            'correct': correct,
            'wrong': wrong,
            'correct_count': correct_count,
            'wrong_count': wrong_count,
            'accuracy': (correct / r['total'] * 100) if r['total'] > 0 else 0
        })
    
    return type_stats

def get_user_category_stats(user_id: int) -> List[Dict[str, Any]]:
    """
    获取用户在所有题库下的分类统计
    
    Args:
        user_id (int): 用户ID
        
    Returns:
        list[dict]: 每个分类统计字典，包含字段：
            - category: 分类名称
            - total: 该分类总答题数
            - correct: 该分类正确题目数
            - wrong: 该分类错误题目数
            - correct_count: 该分类总正确次数
            - wrong_count: 该分类总错误次数
            - accuracy: 该分类正确率百分比 (基于正确题目数量和总答题题目数量)
    """
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT
            q.category,
            COUNT(*) as total,
            COUNT(CASE WHEN h.correct = 1 THEN 1 END) as correct,
            COUNT(CASE WHEN h.correct = 0 THEN 1 END) as wrong,
            SUM(h.correct_count) as correct_count,
            SUM(h.wrong_count) as wrong_count
        FROM history h
        JOIN questions q ON h.question_id = q.id
        WHERE h.user_id = ?
        GROUP BY q.category
    ''', (user_id,))
    
    category_stats = []
    for r in c.fetchall():
        correct = r['correct'] if r['correct'] else 0
        wrong = r['wrong'] if r['wrong'] else 0
        correct_count = r['correct_count'] if r['correct_count'] else 0
        wrong_count = r['wrong_count'] if r['wrong_count'] else 0

        category_stats.append({
            'category': r['category'] or '未分类',
            'total': r['total'],
            'correct': correct,
            'wrong': wrong,
            'correct_count': correct_count,
            'wrong_count': wrong_count,
            'accuracy': (correct / r['total'] * 100) if r['total'] > 0 else 0
        })
    
    return category_stats

def get_user_worst_questions(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """
    获取用户在所有题库中错误次数最多的题目
    
    Args:
        user_id (int): 用户ID
        limit (int): 返回的最大题目数量，默认为10
        
    Returns:
        list[dict]: 题目信息列表，每个字典包含字段：
            - question_id: 题目ID
            - bank_id: 题库ID
            - stem: 题干
            - wrong_times: 错误次数
    """
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT 
            h.question_id, 
            h.bank_id,
            SUM(h.wrong_count) as wrong_times, 
            q.stem
        FROM history h 
        JOIN questions q ON h.question_id = q.id
        WHERE h.user_id = ? AND h.wrong_count > 0 AND h.complete = 1
        GROUP BY h.question_id
        ORDER BY wrong_times DESC
        LIMIT ?
    ''', (user_id, limit))
    
    worst_questions = []
    for r in c.fetchall():
        worst_questions.append({
            'question_id': r['question_id'],
            'bank_id': r['bank_id'],
            'stem': r['stem'],
            'wrong_times': r['wrong_times']
        })
    
    return worst_questions

def get_user_all_favorites(user_id: int) -> List[Dict[str, Any]]:
    """
    获取用户在所有题库中的收藏题目
    
    Args:
        user_id (int): 用户ID
        
    Returns:
        list[dict]: 收藏题目列表，每个字典包含字段：
            - question_id: 题目ID
            - tag: 收藏标签
            - bank_id: 题库ID
            - stem: 题干
            - answer: 答案
            - type: 题型
            - category: 分类
            - bankname: 题库名称
    """
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT 
            f.question_id, 
            f.tag, 
            f.bank_id,
            q.[order],
            q.stem, 
            q.answer, 
            q.type, 
            q.category,
            b.bankname
        FROM favorites f 
        JOIN questions q ON f.question_id = q.id 
        JOIN banks b ON f.bank_id = b.id
        WHERE f.user_id = ?
        ORDER BY f.created_at DESC
    ''', (user_id,))
    
    favorites_data = []
    rows = c.fetchall()
    for r in rows:
        favorites_data.append({
            'question_id': r['question_id'],
            'order': r['order'],
            'tag': r['tag'] or '未标记',
            'stem': r['stem'][:100] + '...' if len(r['stem']) > 100 else r['stem'],
            'answer': r['answer'],
            'type': r['type'],
            'category': r['category'],
            'bank_id': r['bank_id'],
            'bankname': r['bankname']
        })
    
    return favorites_data

def get_user_all_wrong_questions(user_id: int) -> Dict[str, Any]:
    """
    获取用户在所有题库中的错题统计信息
    
    Args:
        user_id (int): 用户ID
        
    Returns:
        dict: 包含以下字段的字典：
            - wrong_questions: 错题列表，每个字典包含：
                - question_id: 题目ID
                - bank_id: 题库ID
                - bankname: 题库名
                - stem: 题干
                - type: 题型
                - category: 分类
                - wrong_count: 错误次数
                - last_wrong_time: 最后错误时间
            - wrong_total_count: 错题总错误次数
            - wrong_unique_categories_count: 错题涉及分类数量
            - wrong_once_count: 只错一次的题目数量
    """
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT
            h.question_id,
            h.bank_id,
            b.bankname,
            q.[order],
            q.stem,
            q.type,
            q.category,
            h.wrong_count,
            h.updated_at AS last_wrong_time 
        FROM history h
        JOIN questions q ON h.question_id = q.id
        JOIN banks b ON h.bank_id = b.id
        WHERE h.user_id = ?
        AND h.correct = 0
        ORDER BY h.updated_at DESC
    ''', (user_id,))
    
    wrong_questions_data = []
    rows = c.fetchall()
    
    wrong_total_count = 0
    wrong_unique_categories = set()
    wrong_once_count = 0
    
    for r in rows:
        wrong_count = r['wrong_count']
        category = r['category']
        
        wrong_questions_data.append({
            'question_id': r['question_id'],
            'order': r['order'],
            'bank_id': r['bank_id'],
            'bankname': r['bankname'],
            'stem': r['stem'][:20] + '...' if len(r['stem']) > 20 else r['stem'],
            'type': r['type'],
            'category': category,
            'wrong_count': wrong_count,
            'last_wrong_time': r['last_wrong_time']
        })
        
        # 统计信息
        wrong_total_count += wrong_count
        if category:
            wrong_unique_categories.add(category)
        if wrong_count == 1:
            wrong_once_count += 1
    
    return {
        'wrong_questions': wrong_questions_data,
        'wrong_total_count': wrong_total_count,
        'wrong_unique_categories_count': len(wrong_unique_categories),
        'wrong_once_count': wrong_once_count
    }

def fetch_user_qids_by_bid(user_id: int, bank_id: int) -> Dict[str, List[int]]:
    """
    获取用户在指定题库下的正确和错误题目ID列表

    Args:
        user_id (int): 用户ID
        bank_id (int): 题库ID

    Returns:
        Dict[str, List[int]]: 包含两个键的字典：
            - 'correct': 正确题目ID列表
            - 'wrong': 错误题目ID列表
    """
    conn = get_db()
    c = conn.cursor()

    try:
        # 查询正确题目
        c.execute('''
            SELECT question_id
            FROM history
            WHERE user_id = ? AND bank_id = ?
              AND complete = 1 AND correct = 1
        ''', (user_id, bank_id))

        correct_rows = c.fetchall()
        correct_ids = [row['question_id'] for row in correct_rows]

        # 查询错误题目
        c.execute('''
            SELECT question_id
            FROM history
            WHERE user_id = ? AND bank_id = ?
              AND complete = 1 AND correct = 0
        ''', (user_id, bank_id))

        wrong_rows = c.fetchall()
        wrong_ids = [row['question_id'] for row in wrong_rows]

        return {
            'correct': correct_ids,
            'wrong': wrong_ids
        }

    except Exception as e:
        # 这里应该有一个logger，但auth.py中没有导入db_logger
        print(f"获取用户{user_id}在题库{bank_id}的题目ID列表失败: {e}")
        return {'correct': [], 'wrong': []}