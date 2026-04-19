"""
examcat - 浏览路由蓝图
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for
import json
from ..utils.auth import login_required, get_user_id, admin_required
from ..utils.database import get_db
from ..utils.banks import get_current_bank_id
from ..utils.questions import is_favorite

browse_bp = Blueprint('browse', __name__, url_prefix='/browse', template_folder='../templates/base')

@browse_bp.route('/')
@login_required
def index():
    """浏览所有题目"""
    user_id = get_user_id()
    current_bank_result = get_current_bank_id(user_id)
    current_bank_id = current_bank_result[0] if current_bank_result else None
    page = request.args.get('page', 1, type=int)
    question_type = request.args.get('type', '')
    search_query = request.args.get('search', '')
    difficulty = request.args.get('difficulty', '')
    category = request.args.get('category', '')
    per_page = 20  # 每页题目数
    
    conn = get_db()
    c = conn.cursor()
    
    # 构建SQL查询条件
    where_conditions = ['bank_id = ?']
    params = [current_bank_id]
    
    if question_type and question_type != 'all':
        where_conditions.append('type = ?')
        params.append(question_type)
    
    if difficulty and difficulty != 'all':
        # 新架构没有difficulty字段，使用type2或忽略
        # where_conditions.append('type2 = ?')
        # params.append(difficulty)
        pass
    
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
        SELECT id, stem, answer, type, type2, category, options, bank_id 
        FROM questions 
        {where_clause}
        ORDER BY id ASC 
        LIMIT ? OFFSET ?
    ''', query_params)
    
    rows = c.fetchall()
    questions = []
    
    for row in rows:
        question_data = {
            'id': row['id'],
            'stem': row['stem'][:150] + '...' if len(row['stem']) > 150 else row['stem'],
            'answer': row['answer'],
            'type': row['type'],
            'type2': row['type2'],
            'category': row['category'],
            'options': json.loads(row['options']) if row['options'] else {},
            'bank_id': row['bank_id']
        }
        
        # 检查是否收藏
        question_data['is_favorite'] = is_favorite(user_id, row['id'])
        
        questions.append(question_data)
    
    # 获取可用的过滤选项
    filters = {
        'types': get_distinct_values(c, 'type', current_bank_id),
        'difficulties': [],  # 新架构没有difficulty字段
        'categories': get_distinct_values(c, 'category', current_bank_id)
    }
    
    
    
    # 计算分页信息
    total_pages = (total + per_page - 1) // per_page
    has_prev = page > 1
    has_next = page < total_pages
    
    # 获取题库名称
    current_bank_name = None
    if current_bank_id:
        c.execute('SELECT bankname FROM banks WHERE id = ?', (current_bank_id,))
        bank_row = c.fetchone()
        current_bank_name = bank_row['bankname'] if bank_row else None
    
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
                          current_bank=current_bank_name,
                          current_bank_id=current_bank_id)

@browse_bp.route('/filter')
@login_required
def filter():
    """高级筛选界面"""
    user_id = get_user_id()
    current_bank_result = get_current_bank_id(user_id)
    current_bank_id = current_bank_result[0] if current_bank_result else None
    
    conn = get_db()
    c = conn.cursor()
    
    # 获取所有可筛选的字段值
    filters = {
        'types': get_distinct_values(c, 'type', current_bank_id),  # 新架构使用type而非qtype
        'difficulties': [],  # 新架构没有difficulty字段
        'categories': get_distinct_values(c, 'category', current_bank_id)
    }
    
    # 获取筛选参数
    question_type = request.args.get('type', '')
    difficulty = request.args.get('difficulty', '')
    category = request.args.get('category', '')
    search_query = request.args.get('search', '')
    
    # 构建查询
    where_conditions = ['bank_id = ?']
    params = [current_bank_id]
    
    if question_type:
        where_conditions.append('type = ?')  # 新架构使用type字段
        params.append(question_type)

    if difficulty:
        # 新架构没有difficulty字段，使用type2作为替代或忽略
        where_conditions.append('type2 = ?')
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
        SELECT id, stem, answer, type, type2, category
        FROM questions
        {where_clause}
        ORDER BY id ASC
    ''', params)
    
    results = []
    for row in c.fetchall():
        results.append({
            'id': row['id'],
            'stem': row['stem'][:100] + '...' if len(row['stem']) > 100 else row['stem'],
            'answer': row['answer'],
            'type': row['type'],
            'type2': row['type2'],  # 替代原来的difficulty
            'category': row['category']
        })
    
    
    # 获取题库名称
    current_bank_name = None
    if current_bank_id:
        c.execute('SELECT bankname FROM banks WHERE id = ?', (current_bank_id,))
        bank_row = c.fetchone()
        current_bank_name = bank_row['bankname'] if bank_row else None

    return render_template('filter.html',
                          filters=filters,
                          results=results,
                          current_type=question_type,
                          current_difficulty=difficulty,
                          current_category=category,
                          current_search=search_query,
                          current_bank=current_bank_name,
                          current_bank_id=current_bank_id)

def get_distinct_values(cursor, column, bank_id):
    """获取指定列的不同值"""
    # 注意：新架构中没有difficulty字段，如果查询difficulty返回空列表
    if column == 'difficulty':
        return []

    cursor.execute(f'''
        SELECT DISTINCT {column} as value
        FROM questions
        WHERE bank_id = ? AND {column} IS NOT NULL AND {column} != ''
        ORDER BY {column}
    ''', (bank_id,))

    return [r['value'] for r in cursor.fetchall()]

@browse_bp.route('/category/<category>')
@login_required
def by_category(category):
    """按分类浏览"""
    user_id = get_user_id()
    current_bank_result = get_current_bank_id(user_id)
    current_bank_id = current_bank_result[0] if current_bank_result else None
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    conn = get_db()
    c = conn.cursor()
    
    # 获取分类下的题目总数
    c.execute('SELECT COUNT(*) as total FROM questions WHERE bank_id = ? AND category = ?',
              (current_bank_id, category))
    total = c.fetchone()['total']
    
    # 获取题目
    offset = (page - 1) * per_page
    c.execute('''
        SELECT id, stem, answer, type, type2, category
        FROM questions
        WHERE bank_id = ? AND category = ?
        ORDER BY id ASC
        LIMIT ? OFFSET ?
    ''', (current_bank_id, category, per_page, offset))
    
    questions = []
    for row in c.fetchall():
        questions.append({
            'id': row['id'],
            'stem': row['stem'][:150] + '...' if len(row['stem']) > 150 else row['stem'],
            'answer': row['answer'],
            'type': row['type'],
            'type2': row['type2'],  # 替代原来的difficulty
            'is_favorite': is_favorite(user_id, row['id'])
        })
    
    
    
    # 获取题库名称
    current_bank_name = None
    if current_bank_id:
        c.execute('SELECT bankname FROM banks WHERE id = ?', (current_bank_id,))
        bank_row = c.fetchone()
        current_bank_name = bank_row['bankname'] if bank_row else None
    
    # 计算分页信息
    total_pages = (total + per_page - 1) // per_page
    
    return render_template('browse_category.html',
                          category=category,
                          questions=questions,
                          page=page,
                          total_pages=total_pages,
                          total=total,
                          current_bank=current_bank_name,
                          current_bank_id=current_bank_id)

@browse_bp.route('/difficulty/<difficulty>')
@login_required
def by_difficulty(difficulty):
    """按难度浏览 - 注意：新架构中使用type2字段替代difficulty"""
    user_id = get_user_id()
    current_bank_result = get_current_bank_id(user_id)
    current_bank_id = current_bank_result[0] if current_bank_result else None
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    conn = get_db()
    c = conn.cursor()
    
    # 获取题库名称
    current_bank_name = None
    if current_bank_id:
        c.execute('SELECT bankname FROM banks WHERE id = ?', (current_bank_id,))
        bank_row = c.fetchone()
        current_bank_name = bank_row['bankname'] if bank_row else None
    
    # 获取type2下的题目总数（使用type2替代difficulty）
    c.execute('SELECT COUNT(*) as total FROM questions WHERE bank_id = ? AND type2 = ?', 
              (current_bank_id, difficulty))
    total = c.fetchone()['total']
    
    # 获取题目
    offset = (page - 1) * per_page
    c.execute('''
        SELECT id, stem, answer, type, type2, category
        FROM questions 
        WHERE bank_id = ? AND type2 = ?
        ORDER BY id ASC 
        LIMIT ? OFFSET ?
    ''', (current_bank_id, difficulty, per_page, offset))
    
    questions = []
    for row in c.fetchall():
        questions.append({
            'id': row['id'],
            'stem': row['stem'][:150] + '...' if len(row['stem']) > 150 else row['stem'],
            'answer': row['answer'],
            'type': row['type'],
            'type2': row['type2'],
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
                          current_bank=current_bank_name,
                          current_bank_id=current_bank_id)

@browse_bp.route('/edit/<question_id>', methods=['GET', 'POST'])
@admin_required
def edit_question(question_id):
    """编辑题目"""
    user_id = get_user_id()
    current_bank_result = get_current_bank_id(user_id)
    current_bank_id = current_bank_result[0] if current_bank_result else None
    
    # 获取题目信息
    from ..utils.questions import fetch_question
    question = fetch_question(question_id)
    if not question:
        flash('题目不存在', 'error')
        return redirect(url_for('browse.index'))
    
    # 检查题目是否属于当前用户的题库
    if question['bank_id'] != current_bank_id:
        flash('您无法编辑此题库的题目', 'error')
        return redirect(url_for('browse.index'))
    
    if request.method == 'POST':
        # 处理表单提交
        stem = request.form.get('stem', '').strip()
        answer = request.form.get('answer', '').strip()
        type2 = request.form.get('difficulty', '未知')  # 表单字段名保持difficulty，但存储为type2
        type_ = request.form.get('qtype', '未知')  # 表单字段名保持qtype，但存储为type
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
        
        # 准备更新数据（新架构字段名）
        updated_data = {
            'stem': stem,
            'answer': answer,
            'type': type_,
            'type2': type2,
            'category': category,
            'options': options
        }
        # 更新题目
        from ..utils.questions import update_question
        success = update_question(question_id, updated_data)
        
        if success:
            flash('题目更新成功', 'success')
            return redirect(url_for('browse.index'))
        else:
            flash('题目更新失败，请重试', 'error')
    
    # 获取题库名称
    current_bank_name = None
    if current_bank_id:
        c.execute('SELECT bankname FROM banks WHERE id = ?', (current_bank_id,))
        bank_row = c.fetchone()
        current_bank_name = bank_row['bankname'] if bank_row else None
    
    # 获取可用的题型、难度和分类选项（用于下拉菜单）
    # 新架构使用type字段替代qtype，type2替代difficulty
    c.execute('SELECT DISTINCT type FROM questions WHERE bank_id = ? AND type IS NOT NULL AND type != ""', (current_bank_id,))
    existing_types = [row['type'] for row in c.fetchall()]

    # 确保至少包含单选题和多选题，同时保持其他已有题型
    standard_types = ['单选题', '多选题']
    # 合并并去重，标准题型放在前面
    all_types_set = set(existing_types)
    all_types_set.update(standard_types)
    available_types = list(all_types_set)

    # 新架构使用type2字段替代difficulty
    c.execute('SELECT DISTINCT type2 FROM questions WHERE bank_id = ? AND type2 IS NOT NULL AND type2 != ""', (current_bank_id,))
    existing_difficulties = [row['type2'] for row in c.fetchall()]

    # 确保至少包含常见的难度等级
    standard_difficulties = ['简单', '中等', '困难']
    all_difficulties_set = set(existing_difficulties)
    all_difficulties_set.update(standard_difficulties)
    available_difficulties = list(all_difficulties_set)

    c.execute('SELECT DISTINCT category FROM questions WHERE bank_id = ? AND category IS NOT NULL AND category != ""', (current_bank_id,))
    available_categories = [row['category'] for row in c.fetchall()]
    
    return render_template('edit_question.html',
                         question=question,
                         available_types=available_types,
                         available_difficulties=available_difficulties,
                         available_categories=available_categories,
                         current_bank=current_bank_name)

@browse_bp.route('/add', methods=['GET', 'POST'])
@admin_required
def add_question():
    """新增题目"""
    user_id = get_user_id()
    current_bank_result = get_current_bank_id(user_id)
    current_bank_id = current_bank_result[0] if current_bank_result else None
    
    conn = get_db()
    c = conn.cursor()
    
    # 获取题库名称
    current_bank_name = None
    if current_bank_id:
        c.execute('SELECT bankname FROM banks WHERE id = ?', (current_bank_id,))
        bank_row = c.fetchone()
        current_bank_name = bank_row['bankname'] if bank_row else None
    
    if request.method == 'POST':
        # 处理表单提交
        stem = request.form.get('stem', '').strip()
        answer = request.form.get('answer', '').strip()
        type2 = request.form.get('difficulty', '未知')  # 表单字段名保持difficulty，但存储为type2
        type_ = request.form.get('qtype', '未知')  # 表单字段名保持qtype，但存储为type
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
        
        # 准备题目数据（新架构字段名）
        question_data = {
            'stem': stem,
            'answer': answer,
            'type': type_,
            'type2': type2,
            'category': category,
            'options': options
        }
        
        # TODO: 新架构的添加题目功能需要实现
        # 添加到数据库和CSV（目前使用旧函数，需要更新）
        from ..utils.questions import add_question_to_db
        # 注意：add_question_to_db需要bank_name参数，且使用旧字段名
        old_format_data = {
            'stem': stem,
            'answer': answer,
            'difficulty': type2,  # 映射到difficulty
            'qtype': type_,  # 映射到qtype
            'category': category,
            'options': options
        }
        success, result = add_question_to_db(current_bank_name, old_format_data)
        
        if success:
            flash(f'题目添加成功！新题目ID: {result}', 'success')
            return redirect(url_for('browse.index'))
        else:
            flash(f'题目添加失败: {result}', 'error')
    
    # 获取可用的题型、难度和分类选项（新架构）
    # 查询数据库中已有的题型（使用type字段）
    c.execute('''
        SELECT DISTINCT type 
        FROM questions 
        WHERE bank_id = ? AND type IS NOT NULL AND type != ''
        ORDER BY type
    ''', (current_bank_id,))
    existing_types = [row['type'] for row in c.fetchall()]
    
    # 标准题型列表
    standard_types = ['单选题', '多选题', '判断题', '填空题', '简答题']
    
    # 合并并去重，标准题型放在前面
    available_types = []
    for stype in standard_types:
        if stype not in available_types:
            available_types.append(stype)
    for etype in existing_types:
        if etype not in available_types:
            available_types.append(etype)
    
    # 查询数据库中已有的难度/类型2（使用type2字段）
    c.execute('''
        SELECT DISTINCT type2 
        FROM questions 
        WHERE bank_id = ? AND type2 IS NOT NULL AND type2 != ''
        ORDER BY type2
    ''', (current_bank_id,))
    existing_difficulties = [row['type2'] for row in c.fetchall()]
    
    # 标准难度等级
    standard_difficulties = ['简单', '中等', '困难']
    
    # 合并并去重，标准难度放在前面
    available_difficulties = []
    for sdifficulty in standard_difficulties:
        if sdifficulty not in available_difficulties:
            available_difficulties.append(sdifficulty)
    for edifficulty in existing_difficulties:
        if edifficulty not in available_difficulties:
            available_difficulties.append(edifficulty)
    
    # 查询分类
    c.execute('SELECT DISTINCT category FROM questions WHERE bank_id = ? AND category IS NOT NULL AND category != "" ORDER BY category', (current_bank_id,))
    available_categories = [row['category'] for row in c.fetchall()]
    
    # 如果没有分类，添加默认分类
    if not available_categories:
        available_categories = ['未分类']
    
    return render_template('add_question.html',
                         available_types=available_types,
                         available_difficulties=available_difficulties,
                         available_categories=available_categories,
                         current_bank=current_bank_name)