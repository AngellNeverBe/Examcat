"""
examcat - 浏览路由蓝图
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for
import json
from ..utils.auth import login_required, get_user_id, admin_required
from ..utils.database import get_db, get_current_bank, get_question_by_id, update_question_in_db, add_question_to_db, get_enhanced_types, get_enhanced_difficulties
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

@browse_bp.route('/edit/<question_id>', methods=['GET', 'POST'])
@admin_required
def edit_question(question_id):
    """编辑题目"""
    user_id = get_user_id()
    current_bank = get_current_bank(user_id)
    
    conn = get_db()
    c = conn.cursor()
    
    # 获取题目信息
    question = get_question_by_id(question_id)
    if not question:
        flash('题目不存在', 'error')
        return redirect(url_for('browse.index'))
    
    # 检查题目是否属于当前用户的题库
    if question['bank_name'] != current_bank:
        flash('您无法编辑此题库的题目', 'error')
        return redirect(url_for('browse.index'))
    
    if request.method == 'POST':
        # 处理表单提交
        stem = request.form.get('stem', '').strip()
        answer = request.form.get('answer', '').strip()
        difficulty = request.form.get('difficulty', '未知')
        qtype = request.form.get('qtype', '未知')
        category = request.form.get('category', '未分类')
        
        # 收集选项
        options = {}
        for opt in ['A', 'B', 'C', 'D', 'E']:
            option_value = request.form.get(f'option_{opt}', '').strip()
            if option_value:
                options[opt] = option_value
        
        # 验证必填字段
        if not stem:
            flash('题干不能为空', 'error')
            return render_template('edit_question.html', question=question)
        
        if not answer:
            flash('答案不能为空', 'error')
            return render_template('edit_question.html', question=question)
        
        # 准备更新数据
        updated_data = {
            'stem': stem,
            'answer': answer,
            'difficulty': difficulty,
            'qtype': qtype,
            'category': category,
            'options': options
        }
        # 更新题目
        success = update_question_in_db(question_id, updated_data)
        
        if success:
            flash('题目更新成功', 'success')
            return redirect(url_for('browse.index'))
        else:
            flash('题目更新失败，请重试', 'error')
    
    # 获取可用的题型、难度和分类选项（用于下拉菜单）
    c.execute('SELECT DISTINCT qtype FROM questions WHERE bank_name = ? AND qtype IS NOT NULL AND qtype != ""', (current_bank,))
    existing_types = [row['qtype'] for row in c.fetchall()]

    # 确保至少包含单选题和多选题，同时保持其他已有题型
    standard_types = ['单选题', '多选题']
    # 合并并去重，标准题型放在前面
    all_types_set = set(existing_types)
    all_types_set.update(standard_types)
    available_types = list(all_types_set)

    c.execute('SELECT DISTINCT difficulty FROM questions WHERE bank_name = ? AND difficulty IS NOT NULL AND difficulty != ""', (current_bank,))
    existing_difficulties = [row['difficulty'] for row in c.fetchall()]

    # 确保至少包含常见的难度等级
    standard_difficulties = ['简单', '中等', '困难']
    all_difficulties_set = set(existing_difficulties)
    all_difficulties_set.update(standard_difficulties)
    available_difficulties = list(all_difficulties_set)

    c.execute('SELECT DISTINCT category FROM questions WHERE bank_name = ? AND category IS NOT NULL AND category != ""', (current_bank,))
    available_categories = [row['category'] for row in c.fetchall()]
    
    return render_template('edit_question.html',
                         question=question,
                         available_types=available_types,
                         available_difficulties=available_difficulties,
                         available_categories=available_categories,
                         current_bank=current_bank)

@browse_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_question():
    """新增题目"""
    user_id = get_user_id()
    current_bank = get_current_bank(user_id)
    
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'POST':
        # 处理表单提交
        stem = request.form.get('stem', '').strip()
        answer = request.form.get('answer', '').strip()
        difficulty = request.form.get('difficulty', '未知')
        qtype = request.form.get('qtype', '未知')
        category = request.form.get('category', '未分类')
        
        # 收集选项
        options = {}
        for opt in ['A', 'B', 'C', 'D', 'E']:
            option_value = request.form.get(f'option_{opt}', '').strip()
            if option_value:
                options[opt] = option_value
        
        # 验证必填字段
        if not stem:
            flash('题干不能为空', 'error')
            return redirect(url_for('browse.add_question'))
        
        if not answer:
            flash('答案不能为空', 'error')
            return redirect(url_for('browse.add_question'))
        
        # 准备题目数据
        question_data = {
            'stem': stem,
            'answer': answer,
            'difficulty': difficulty,
            'qtype': qtype,
            'category': category,
            'options': options
        }
        
        # 添加到数据库和CSV
        success, result = add_question_to_db(current_bank, question_data)
        
        if success:
            flash(f'题目添加成功！新题目ID: {result}', 'success')
            return redirect(url_for('browse.index'))
        else:
            flash(f'题目添加失败: {result}', 'error')
    
    # 获取可用的题型、难度和分类选项
    available_types = get_enhanced_types(c, current_bank)
    available_difficulties = get_enhanced_difficulties(c, current_bank)
    
    c.execute('SELECT DISTINCT category FROM questions WHERE bank_name = ? AND category IS NOT NULL AND category != "" ORDER BY category', (current_bank,))
    available_categories = [row['category'] for row in c.fetchall()]
    
    # 如果没有分类，添加默认分类
    if not available_categories:
        available_categories = ['未分类']
    
    return render_template('add_question.html',
                         available_types=available_types,
                         available_difficulties=available_difficulties,
                         available_categories=available_categories,
                         current_bank=current_bank)