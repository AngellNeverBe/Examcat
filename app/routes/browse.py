"""
examcat - 浏览路由蓝图
"""
from flask import Blueprint, render_template, request
import json
from ..utils.auth import login_required, get_user_id
from ..utils.database import get_db, get_current_bank
from ..utils.questions import is_favorite

browse_bp = Blueprint('browse', __name__, url_prefix='/browse', template_folder='../templates/base')

@browse_bp.route('/')
@login_required
def index():
    """浏览所有题目"""
    user_id = get_user_id()
    current_bank = get_current_bank(user_id)
    page = request.args.get('page', 1, type=int)
    question_type = request.args.get('type', '')
    search_query = request.args.get('search', '')
    difficulty = request.args.get('difficulty', '')
    category = request.args.get('category', '')
    per_page = 20  # 每页题目数
    
    conn = get_db()
    c = conn.cursor()
    
    # 构建SQL查询条件
    where_conditions = ['bank_name = ?']
    params = [current_bank]
    
    if question_type and question_type != 'all':
        where_conditions.append('qtype = ?')
        params.append(question_type)
    
    if difficulty and difficulty != 'all':
        where_conditions.append('difficulty = ?')
        params.append(difficulty)
    
    if category and category != 'all':
        where_conditions.append('category = ?')
        params.append(category)
    
    if search_query:
        where_conditions.append('(stem LIKE ? OR id LIKE ?)')
        params.extend(['%' + search_query + '%', '%' + search_query + '%'])
    
    where_clause = ' WHERE ' + ' AND '.join(where_conditions) if where_conditions else ''
    
    # 获取总数
    count_sql = f'SELECT COUNT(*) as total FROM questions{where_clause}'
    c.execute(count_sql, params)
    total = c.fetchone()['total']
    
    # 获取题目（带分页）
    offset = (page - 1) * per_page
    query_params = params + [per_page, offset]
    c.execute(f'''
        SELECT id, stem, answer, difficulty, qtype, category, options 
        FROM questions 
        {where_clause}
        ORDER BY CAST(id AS INTEGER) ASC 
        LIMIT ? OFFSET ?
    ''', query_params)
    
    rows = c.fetchall()
    questions = []
    
    for row in rows:
        question_data = {
            'id': row['id'],
            'stem': row['stem'][:150] + '...' if len(row['stem']) > 150 else row['stem'],
            'answer': row['answer'],
            'difficulty': row['difficulty'],
            'type': row['qtype'],
            'category': row['category'],
            'options': json.loads(row['options']) if row['options'] else {}
        }
        
        # 检查是否收藏
        question_data['is_favorite'] = is_favorite(user_id, row['id'])
        
        questions.append(question_data)
    
    # 获取可用的过滤选项
    filters = {
        'types': get_distinct_values(c, 'qtype', current_bank),
        'difficulties': get_distinct_values(c, 'difficulty', current_bank),
        'categories': get_distinct_values(c, 'category', current_bank)
    }
    
    
    
    # 计算分页信息
    total_pages = (total + per_page - 1) // per_page
    has_prev = page > 1
    has_next = page < total_pages
    
    return render_template('browse.html',
                          questions=questions,
                          total=total,
                          page=page,
                          per_page=per_page,
                          total_pages=total_pages,
                          has_prev=has_prev,
                          has_next=has_next,
                          filters=filters,
                          current_type=question_type,
                          current_difficulty=difficulty,
                          current_category=category,
                          current_search=search_query,
                          current_bank=current_bank)

@browse_bp.route('/filter')
@login_required
def filter():
    """高级筛选界面"""
    user_id = get_user_id()
    current_bank = get_current_bank(user_id)
    
    conn = get_db()
    c = conn.cursor()
    
    # 获取所有可筛选的字段值
    filters = {
        'types': get_distinct_values(c, 'qtype', current_bank),
        'difficulties': get_distinct_values(c, 'difficulty', current_bank),
        'categories': get_distinct_values(c, 'category', current_bank)
    }
    
    # 获取筛选参数
    question_type = request.args.get('type', '')
    difficulty = request.args.get('difficulty', '')
    category = request.args.get('category', '')
    search_query = request.args.get('search', '')
    
    # 构建查询
    where_conditions = ['bank_name = ?']
    params = [current_bank]
    
    if question_type:
        where_conditions.append('qtype = ?')
        params.append(question_type)
    
    if difficulty:
        where_conditions.append('difficulty = ?')
        params.append(difficulty)
    
    if category:
        where_conditions.append('category = ?')
        params.append(category)
    
    if search_query:
        where_conditions.append('(stem LIKE ? OR id LIKE ?)')
        params.extend(['%' + search_query + '%', '%' + search_query + '%'])
    
    where_clause = ' WHERE ' + ' AND '.join(where_conditions) if where_conditions else ''
    
    # 执行查询
    c.execute(f'''
        SELECT id, stem, answer, difficulty, qtype, category
        FROM questions 
        {where_clause}
        ORDER BY CAST(id AS INTEGER) ASC
    ''', params)
    
    results = []
    for row in c.fetchall():
        results.append({
            'id': row['id'],
            'stem': row['stem'][:100] + '...' if len(row['stem']) > 100 else row['stem'],
            'answer': row['answer'],
            'difficulty': row['difficulty'],
            'type': row['qtype'],
            'category': row['category']
        })
    
    
    
    return render_template('filter.html',
                          filters=filters,
                          results=results,
                          current_type=question_type,
                          current_difficulty=difficulty,
                          current_category=category,
                          current_search=search_query,
                          current_bank=current_bank)

def get_distinct_values(cursor, column, bank_name):
    """获取指定列的不同值"""
    cursor.execute(f'''
        SELECT DISTINCT {column} as value 
        FROM questions 
        WHERE bank_name = ? AND {column} IS NOT NULL AND {column} != ''
        ORDER BY {column}
    ''', (bank_name,))
    
    return [r['value'] for r in cursor.fetchall()]

@browse_bp.route('/category/<category>')
@login_required
def by_category(category):
    """按分类浏览"""
    user_id = get_user_id()
    current_bank = get_current_bank(user_id)
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    conn = get_db()
    c = conn.cursor()
    
    # 获取分类下的题目总数
    c.execute('SELECT COUNT(*) as total FROM questions WHERE bank_name = ? AND category = ?', 
              (current_bank, category))
    total = c.fetchone()['total']
    
    # 获取题目
    offset = (page - 1) * per_page
    c.execute('''
        SELECT id, stem, answer, difficulty, qtype, category
        FROM questions 
        WHERE bank_name = ? AND category = ?
        ORDER BY CAST(id AS INTEGER) ASC 
        LIMIT ? OFFSET ?
    ''', (current_bank, category, per_page, offset))
    
    questions = []
    for row in c.fetchall():
        questions.append({
            'id': row['id'],
            'stem': row['stem'][:150] + '...' if len(row['stem']) > 150 else row['stem'],
            'answer': row['answer'],
            'difficulty': row['difficulty'],
            'type': row['qtype'],
            'is_favorite': is_favorite(user_id, row['id'])
        })
    
    
    
    # 计算分页信息
    total_pages = (total + per_page - 1) // per_page
    
    return render_template('browse_category.html',
                          category=category,
                          questions=questions,
                          page=page,
                          total_pages=total_pages,
                          total=total,
                          current_bank=current_bank)

@browse_bp.route('/difficulty/<difficulty>')
@login_required
def by_difficulty(difficulty):
    """按难度浏览"""
    user_id = get_user_id()
    current_bank = get_current_bank(user_id)
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    conn = get_db()
    c = conn.cursor()
    
    # 获取难度下的题目总数
    c.execute('SELECT COUNT(*) as total FROM questions WHERE bank_name = ? AND difficulty = ?', 
              (current_bank, difficulty))
    total = c.fetchone()['total']
    
    # 获取题目
    offset = (page - 1) * per_page
    c.execute('''
        SELECT id, stem, answer, difficulty, qtype, category
        FROM questions 
        WHERE bank_name = ? AND difficulty = ?
        ORDER BY CAST(id AS INTEGER) ASC 
        LIMIT ? OFFSET ?
    ''', (current_bank, difficulty, per_page, offset))
    
    questions = []
    for row in c.fetchall():
        questions.append({
            'id': row['id'],
            'stem': row['stem'][:150] + '...' if len(row['stem']) > 150 else row['stem'],
            'answer': row['answer'],
            'difficulty': row['difficulty'],
            'type': row['qtype'],
            'is_favorite': is_favorite(user_id, row['id'])
        })
    
    
    
    # 计算分页信息
    total_pages = (total + per_page - 1) // per_page
    
    return render_template('browse_difficulty.html',
                          difficulty=difficulty,
                          questions=questions,
                          page=page,
                          total_pages=total_pages,
                          total=total,
                          current_bank=current_bank)