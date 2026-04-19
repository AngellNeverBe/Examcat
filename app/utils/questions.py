"""
examcat - 题目辅助函数
"""
import json
import csv
import os
from typing import Tuple, List, Optional, Dict, Any
from flask import request
from .database import get_db, db_logger
from .cookie import cookie_logger
from .banks import get_current_bank_id

# ======== 核心操作 ========
def fetch_question(question_id: int) -> Optional[Dict[str, Any]]:
    """
    根据题目 ID 从数据库中获取完整的题目信息。

    Args:
        question_id (int): 题目的唯一标识 ID（数据库主键）。

    Returns:
        question_data (Optional[Dict[str, Any]]): 
            如果找到题目，返回包含以下字段的字典：
                - id (int): 题目 ID
                - order (int): 题号
                - bank_id (int): 题库 ID
                - stem (str): 题干
                - answer (str): 答案
                - type (str): 主要题型
                - type2 (str): 次要题型
                - category (str): 题目分类
                - options (dict): 选项字典，键为 'A'/'B'/'C'/'D'/'E'，值为选项内容
            如果未找到，返回 None。

    Example:
        >>> question = fetch_question(123)
        >>> if question:
        ...     print(f"题干: {question['stem']}")
        ...     print(f"选项: {question['options']}")
        ... else:
        ...     print("题目不存在")
    """
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM questions WHERE id=?', (question_id,))
    row = c.fetchone()    
    
    if row:
        return {
            'id': row['id'],
            'order': row['order'],
            'bank_id': row['bank_id'],
            'stem': row['stem'],
            'answer': row['answer'],            
            'type': row['type'],
            'type2': row['type2'],
            'category': row['category'],
            'options': json.loads(row['options']) if row['options'] else {}
        }
    return None

def get_first_question_id(user_id: int) -> Tuple[Optional[int], Dict[str, str]]:
    """
    获取用户在当前题库中 order 为 1 的题目 ID, 含cookie

    Args:
        user_id (int): 用户 ID。

    Returns:
        Tuple[Optional[int], Dict[str, str]]:
            - question_id: 题目 ID，若无则返回 None。
            - cookie_dict: 若找到题目，则返回 {'current_seq_qid': str(question_id)}，否则为空字典。
    """
    COOKIE_KEY = 'current_seq_qid'

    # 1. 获取用户当前题库 ID
    current_bank_id = get_current_bank_id(user_id)[0]

    # 2. 查询该题库中 order = 1 的题目
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('''
            SELECT id
            FROM questions
            WHERE bank_id = ? AND "order" = 1
            LIMIT 1
        ''', (current_bank_id,))
        row = c.fetchone()
        if row:
            question_id = row['id']
            return question_id, {COOKIE_KEY: str(question_id)}
    except Exception as e:
        db_logger.error(f"查询第一题失败: {e}")
        return None, {}

def get_current_sequential_question_id(user_id: int) -> Tuple[Optional[int], Dict[str, str]]:
    """
    获取用户在当前题库中已答题目的最大order对应的题目ID，使用cookie缓存
    
    Args:
        user_id (int): 用户ID
        
    Returns:
        tuple: (question_id, cookie_dict)
               question_id: 最大order对应的题目ID，如果找不到返回None
               cookie_dict: 需要设置的cookie字典（仅包含question_id），如果为空表示cookie已存在

    Examples:
        >>> from flask import make_response, jsonify
        >>> from ..utils.cookie import set_cookies_from_dict
        >>> from ..utils.question import get_current_sequential_question_id
        ... 
        >>> cookies = None
        >>> question_id, cookies = get_current_sequential_question_id(user_id)
        >>> resp = make_response(jsonify({'question_id': question_id}))
        >>> if cookies:
        ...     resp = set_cookies_from_dict(resp, cookies)
        >>> return resp
    """
    cookie_key = 'current_seq_qid'
    
    try:
        # 尝试从cookie获取
        if request and hasattr(request, 'cookies'):
            cookie_value = request.cookies.get(cookie_key)
            if cookie_value and cookie_value.isdigit():
                question_id = int(cookie_value)

                # ====!!!! 这里留了一个BUG：未判断题目是否属于当前题库 !!!!====
                cookie_logger.debug(f"从cookie获取用户 {user_id} 当前顺序题目ID: {question_id}")
                return question_id, {}  # 返回数据和空cookie字典
    except Exception as e:
        cookie_logger.debug(f"读取cookie失败: {e}")
    
    # 从数据库获取
    try:
        # 1. 获取用户当前题库ID
        current_bank_id = get_current_bank_id(user_id)[0]  # 只取bank_id部分
        if not current_bank_id:
            db_logger.warning(f"用户 {user_id} 没有当前题库")
            return None, {}
        
        # 2. 查找用户在当前题库中已答题目的最大order对应的题目ID
        question_id = get_bank_sequential_question_id(user_id, current_bank_id)
        
        if question_id:
            return question_id, {cookie_key: str(question_id)}
        else:
            return None, {}
            
    except Exception as e:
        return None, {}

def get_next_sequential_question_id(current_seq_qid: int) -> Optional[int]:
    """
    获取当前题目的下一题（按order顺序）
    
    Args:
        current_seq_qid (int): 当前题目ID
        
    Returns:
        next_qid (Optional[int]): 下一题的题目ID，如果没有下一题则返回None

    Examples:
        >>> next_qid = get_next_sequential_question_id(10)
        >>> if next_qid:
        ...     print(f"下一题ID是: {next_qid}")
        ... else:
        ...     print("这已经是最后一题了")        
    """
    conn = get_db()
    c = conn.cursor()
    
    try:
        # 1. 获取当前题目的order和bank_id
        c.execute('''
            SELECT "order", bank_id 
            FROM questions 
            WHERE id = ?
        ''', (current_seq_qid,))
        
        current_row = c.fetchone()
        if not current_row:
            # logger.warning(f"题目ID {current_seq_qid} 不存在")
            return None
        
        current_order = current_row['order']
        bank_id = current_row['bank_id']
        
        # 2. 查找同一bank_id中order+1的题目
        c.execute('''
            SELECT id 
            FROM questions 
            WHERE bank_id = ? AND "order" = ?
            ORDER BY "order" ASC
            LIMIT 1
        ''', (bank_id, current_order + 1))
        
        next_row = c.fetchone()
        next_qid = next_row['id'] if next_row else None
        return next_qid
            
    except Exception as e:
        db_logger.error(f"获取下一题失败，当前题目ID: {current_seq_qid}, 错误: {e}")
        return None

def get_prev_sequential_question_id(current_seq_qid: int) -> Optional[int]:
    """
    获取当前顺序题目的前一题ID（根据order）
    
    Args:
        current_seq_qid (int): 当前题目的ID。
        
    Returns:
        prev_qid (Optional[int]): 前一题的ID，如果不存在（已是第一题或查询出错）则返回 None。
        
    Examples:
        >>> prev_id = get_prev_sequential_question_id(123)
        >>> if prev_id:
        ...     print(f"上一题ID: {prev_id}")
        ... else:
        ...     print("已是第一题")
    """
    conn = get_db()
    c = conn.cursor()
    
    try:
        # 获取当前题目的order和bank_id
        c.execute('''
            SELECT "order", bank_id 
            FROM questions 
            WHERE id = ?
        ''', (current_seq_qid,))
        
        current_row = c.fetchone()
        if not current_row:
            return None
        
        current_order = current_row['order']
        bank_id = current_row['bank_id']
        
        # 查找同一bank_id中order-1的题目
        c.execute('''
            SELECT id 
            FROM questions 
            WHERE bank_id = ? AND "order" = ?
            ORDER BY "order" ASC
            LIMIT 1
        ''', (bank_id, current_order - 1))
        
        prev_row = c.fetchone()
        prev_qid = prev_row['id'] if prev_row else None
        return prev_qid
            
    except Exception as e:
        db_logger.error(f"获取前一题失败: {e}")
        return None

def get_bank_sequential_question_id(user_id: int, bank_id: int) -> Optional[int]:
    """
    获取用户在某题库下已答题目的最大order对应的题目ID
    
    Args:
        user_id (int): 用户ID
        
    Returns:
        question_id (Optional[int]): 最大order对应的题目ID，如果找不到返回None
    """
    conn = get_db()
    c = conn.cursor()
    
    try:      
        # 查找用户在该题库中已答题目的最大order对应的题目ID
        c.execute('''
            SELECT q.id, q."order"
            FROM history h
            JOIN questions q ON h.question_id = q.id
            WHERE h.user_id = ? 
              AND h.bank_id = ? 
              AND h.complete = 1
            ORDER BY q."order" DESC
            LIMIT 1
        ''', (user_id, bank_id))
        
        row = c.fetchone()
        
        if row:
            question_id = row['id']
            order = row['order']
            
            db_logger.debug(f"从数据库获取用户 {user_id} 当前顺序题目ID: {question_id}, order: {order}, 题库ID: {bank_id}")
            return question_id
        else:
            db_logger.debug(f"用户 {user_id} 在题库 {bank_id} 中没有已答题目")
            return None
            
    except Exception as e:
        db_logger.error(f"获取用户 {user_id} 当前顺序题目ID失败: {e}")
        return None

# ======== 次要功能 ========

def get_random_question_ids(num: int, user_id: int) -> List[int]:
    """
    从当前题库中获取指定数量的随机题目 ID。
    
    Args:
        num (int): 需要获取的题目 ID 数量
        user_id (int): 用户 ID，用于获取当前题库
        
    Returns:
        list[int]: 随机题目 ID 列表
    """
    current_bank_id = get_current_bank_id(user_id)[0]
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id FROM questions WHERE bank_id = ? ORDER BY RANDOM() LIMIT ?', 
              (current_bank_id, num))
    rows = c.fetchall()
    
    return [r['id'] for r in rows]

def is_favorite(user_id: int, question_id: int) -> bool:
    """
    检查用户是否收藏了某道题目。
    
    Args:
        user_id (int): 用户ID
        question_id (int): 题目ID
        
    Returns:
        bool: 已收藏返回 True，否则返回 False
    """
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT 1 FROM favorites WHERE user_id=? AND question_id=?',
              (user_id, question_id))
    is_fav = bool(c.fetchone())
    
    return is_fav

def get_question_completion(user_id: int, question_id: int) -> Dict[str, Any]:
    """
    获取用户对题目的完成状态
    
    Args:
        user_id (int): 用户ID
        question_id (int): 题目ID
        
    Returns:
        dict: 包含完成状态的字典，格式为：
            {
                'completed': bool,           # 是否已完成
                'last_answer': str or None,  # 最后答案
                'correct': bool or None,     # 是否正确
                'complete': int or None,     # complete字段值（0/1）
                'user_answer': str or None   # 用户答案（格式化后）
            }
    """
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute('''
            SELECT complete, last_answer, correct 
            FROM history 
            WHERE user_id = ? AND question_id = ?
        ''', (user_id, question_id))
        
        row = c.fetchone()
        
        if row and row['complete'] == 1:
            # 题目已完成
            last_answer = row['last_answer'] if row['last_answer'] else ''
            return {
                'completed': True,
                'last_answer': last_answer,
                'correct': row['correct'],
                'user_answer': list(last_answer) if last_answer else []  # 转换为列表方便模板使用
            }
        else:
            # 没有记录或complete=0，表示未完成
            return {
                'completed': False,
                'last_answer': None,
                'correct': 0,
                'user_answer': []
            }
            
    except Exception as e:
        db_logger.error(f"获取题目完成状态失败，用户ID {user_id}，题目ID {question_id}: {e}")
        return {
            'completed': False,
            'last_answer': None,
            'correct': 0,
            'user_answer': []
        }

# ======== 修改操作 ========
def update_question(question_id: int, updated_data: Dict[str, Any]) -> bool:
    """
    更新数据库中的题目信息（适配新表结构）

    Args:
        question_id (int): 题目ID（新表为INTEGER）
        updated_data (dict): 更新后的题目数据，可包含字段：
            stem, answer, type, type2, category, options

    Returns:
        bool: 是否成功更新
    """
    conn = get_db()
    c = conn.cursor()

    try:
        # 1. 检查题目是否存在，并获取其 bank_id
        c.execute('SELECT bank_id FROM questions WHERE id = ?', (question_id,))
        row = c.fetchone()
        if not row:
            return False

        bank_id = row['bank_id']

        # 2. 构建更新字段列表（只更新传入的非空字段）
        update_fields = []
        params = []

        # 允许更新的字段映射（key: 数据库字段名, value: 从updated_data中获取的键名）
        allowed_fields = {
            'stem': 'stem',
            'answer': 'answer',
            'type': 'type',
            'type2': 'type2',
            'category': 'category',
            'options': 'options'
        }

        for db_field, data_key in allowed_fields.items():
            if data_key in updated_data:
                value = updated_data[data_key]
                # options 需要 JSON 序列化
                if db_field == 'options' and value is not None:
                    value = json.dumps(value, ensure_ascii=False)
                update_fields.append(f"{db_field} = ?")
                params.append(value)

        # 如果没有字段需要更新，直接返回成功
        if not update_fields:
            return True

        # 3. 执行更新
        params.append(question_id)  # WHERE 条件参数
        sql = f"UPDATE questions SET {', '.join(update_fields)} WHERE id = ?"
        c.execute(sql, params)
        conn.commit()

        db_logger.info(f"Updated question {question_id} in database")

        # 4. 同步更新 CSV 文件（需要从 banks 表获取 bank_name）
        #    注意：CSV 更新函数仍使用 bank_name，这里保持兼容
        c.execute('SELECT bankname FROM banks WHERE id = ?', (bank_id,))
        bank_row = c.fetchone()
        if bank_row:
            bank_name = bank_row['bankname']
            success = update_question_in_csv(bank_name, question_id, updated_data)
            if not success:
                db_logger.warning(f"Failed to update CSV for question {question_id}")
        else:
            db_logger.warning(f"Bank not found for bank_id {bank_id}, CSV update skipped")

        return True

    except Exception as e:
        db_logger.error(f"Error updating question {question_id}: {e}")
        conn.rollback()
        return False

def update_question_in_csv(bank_name: str, question_id: int, updated_data: Dict[str, Any]) -> bool:
    """
    更新CSV文件中的题目信息（适配新表头）

    Args:
        bank_name (str): 题库名称（不带.csv后缀）
        question_id (int): 题目ID（数据库主键）
        updated_data (dict): 更新后的题目数据，包含字段：
            stem, answer, type, type2, category, options

    Returns:
        bool: 是否成功更新
    """
    conn = None
    try:
        # 1. 查询题目在数据库中的 order 和 bank_id
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT "order", bank_id FROM questions WHERE id = ?', (question_id,))
        row = c.fetchone()
        if not row:
            db_logger.error(f"Question {question_id} not found in database")
            return False

        order = row['order']
        bank_id = row['bank_id']

        # 2. 验证 bank_name 是否匹配
        c.execute('SELECT bankname FROM banks WHERE id = ?', (bank_id,))
        bank_row = c.fetchone()
        if not bank_row or bank_row['bankname'] != bank_name:
            db_logger.error(f"Bank name mismatch: {bank_name} vs {bank_row['bankname'] if bank_row else 'None'}")
            return False

        # 3. 构建CSV文件路径
        csv_file = os.path.join('./questions-bank', f"{bank_name}.csv")
        if not os.path.exists(csv_file):
            db_logger.warning(f"CSV file not found: {csv_file}")
            return False

        # 4. 读取CSV文件
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = reader.fieldnames

        # 确保CSV包含必要的列（如果缺少“次要题型”则添加）
        if '次要题型' not in fieldnames:
            fieldnames = list(fieldnames) + ['次要题型']
            for row in rows:
                row['次要题型'] = row.get('次要题型', '')

        # 5. 根据题号（order）查找并更新行
        updated = False
        for i, row in enumerate(rows):
            # CSV中的“题号”是字符串，可能包含空格，需要转换为整数比较
            try:
                csv_order = int(row.get('题号', ''))
            except ValueError:
                continue  # 如果题号不是数字，跳过该行

            if csv_order == order:
                # 更新各字段
                rows[i]['题干'] = updated_data.get('stem', row.get('题干', ''))
                rows[i]['答案'] = updated_data.get('answer', row.get('答案', ''))
                rows[i]['题型'] = updated_data.get('type', row.get('题型', ''))
                rows[i]['次要题型'] = updated_data.get('type2', row.get('次要题型', ''))
                rows[i]['类别'] = updated_data.get('category', row.get('类别', '未分类'))

                # 更新选项（A,B,C,D,E）
                options = updated_data.get('options', {})
                for opt in ['A', 'B', 'C', 'D', 'E']:
                    if opt in options:
                        rows[i][opt] = options[opt]
                    elif opt in rows[i]:
                        rows[i][opt] = ''  # 清空不存在的选项

                updated = True
                break

        if not updated:
            db_logger.warning(f"Question with order {order} not found in CSV file {bank_name}.csv")
            return False

        # 6. 写回CSV文件（保持原字段顺序）
        with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        db_logger.info(f"Updated question {question_id} (order {order}) in CSV file {bank_name}.csv")
        return True

    except Exception as e:
        db_logger.error(f"Error updating CSV for question {question_id}: {e}")
        return False
    finally:
        if conn:
            conn.close()

# !!!!!!!! 未修改的 !!!!!!!!
def add_question_to_db(bank_name, question_data):
    """
    向数据库和CSV文件添加新题目
    
    Args:
        bank_name (str): 题库名称（不带.csv后缀）
        question_data (dict): 题目数据
        
    Returns:
        tuple: (成功状态, 新题目ID或错误消息)
    """
    conn = get_db()
    c = conn.cursor()
    
    try:
        # 1. 生成新的题目ID
        # 获取当前题库中最大的数字ID
        c.execute('''
            SELECT id FROM questions 
            WHERE bank_name = ? 
            ORDER BY CAST(
                CASE 
                    WHEN instr(id, '_') > 0 THEN substr(id, instr(id, '_') + 1)
                    ELSE id 
                END 
            AS INTEGER) DESC
            LIMIT 1
        ''', (bank_name,))
        
        max_id_row = c.fetchone()
        max_num = 0
        
        if max_id_row:
            # 从ID中提取数字部分
            last_id = max_id_row['id']
            if '_' in last_id:
                num_part = last_id.split('_', 1)[1]
            else:
                num_part = last_id
            
            try:
                max_num = int(num_part)
            except ValueError:
                max_num = 0
        
        # 生成新ID（数字部分+1）
        new_id_num = max_num + 1
        new_question_id = f"{bank_name}_{new_id_num}"
        
        # 2. 准备插入数据
        stem = question_data.get('stem', '').strip()
        answer = question_data.get('answer', '').strip()
        difficulty = question_data.get('difficulty', '未知')
        qtype = question_data.get('qtype', '未知')
        category = question_data.get('category', '未分类')
        options = json.dumps(question_data.get('options', {}), ensure_ascii=False)
        
        # 3. 插入到数据库
        c.execute('''
            INSERT INTO questions (id, stem, answer, difficulty, qtype, category, options, bank_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (new_question_id, stem, answer, difficulty, qtype, category, options, bank_name))
        
        conn.commit()
        
        # 4. 同步到CSV文件
        success = add_question_to_csv(bank_name, new_id_num, question_data)
        
        if success:
            db_logger.info(f"Added new question {new_question_id} to database and CSV")
            return True, new_question_id
        else:
            # CSV写入失败，回滚数据库操作
            conn.rollback()
            return False, "CSV文件写入失败"
            
    except Exception as e:
        print(f"Error adding question to database: {e}")
        db_logger.error(f"Error adding question: {e}")
        conn.rollback()
        return False, str(e)

def add_question_to_csv(bank_name, question_num, question_data):
    """
    向CSV文件添加新题目
    
    Args:
        bank_name (str): 题库名称（不带.csv后缀）
        question_num (int): 题目编号
        question_data (dict): 题目数据
        
    Returns:
        bool: 是否成功添加
    """
    try:
        # 构建CSV文件路径
        csv_file = os.path.join('./questions-bank', f"{bank_name}.csv")
        
        # 如果CSV文件不存在，创建新文件
        if not os.path.exists(csv_file):
            print(f"CSV file not found, creating new: {csv_file}")
            create_new_csv_file(csv_file)
        
        # 读取现有数据
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = reader.fieldnames
        
        # 准备新行数据
        new_row = {
            '题号': str(question_num),
            '题干': question_data.get('stem', ''),
            '答案': question_data.get('answer', ''),
            '难度': question_data.get('difficulty', '未知'),
            '题型': question_data.get('qtype', '未知'),
            '类别': question_data.get('category', '未分类')
        }
        
        # 添加选项
        options = question_data.get('options', {})
        for opt in ['A', 'B', 'C', 'D', 'E']:
            if opt in options:
                new_row[opt] = options[opt]
            else:
                new_row[opt] = ''
        
        # 确保所有字段都存在
        for field in fieldnames:
            if field not in new_row:
                new_row[field] = ''
        
        # 添加新行
        rows.append(new_row)
        
        # 写回CSV文件
        with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        db_logger.info(f"Added question {question_num} to CSV file {bank_name}.csv")
        return True
        
    except Exception as e:
        print(f"Error adding question to CSV: {e}")
        db_logger.error(f"Error adding question to CSV: {e}")
        return False

def create_new_csv_file(csv_file_path):
    """
    创建新的CSV文件并写入表头
    
    Args:
        csv_file_path (str): CSV文件路径
    """
    fieldnames = ['题号', '题干', '答案', '难度', '题型', '类别', 'A', 'B', 'C', 'D', 'E']
    
    with open(csv_file_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
    
    print(f"Created new CSV file: {csv_file_path}")

def get_enhanced_types(cursor, bank_name):
    """
    获取增强的题型列表，确保至少包含标准题型
    
    Args:
        cursor: 数据库游标
        bank_name (str): 题库名称
        
    Returns:
        list: 题型列表（包含所有已有题型和标准题型）
    """
    # 查询数据库中已有的题型
    cursor.execute('''
        SELECT DISTINCT qtype 
        FROM questions 
        WHERE bank_name = ? AND qtype IS NOT NULL AND qtype != ''
        ORDER BY qtype
    ''', (bank_name,))
    existing_types = [row['qtype'] for row in cursor.fetchall()]
    
    # 标准题型列表
    standard_types = ['单选题', '多选题', '判断题', '填空题', '简答题']
    
    # 合并并去重，标准题型放在前面
    all_types = []
    
    # 先添加标准题型（如果存在）
    for stype in standard_types:
        if stype not in all_types:
            all_types.append(stype)
    
    # 再添加其他已有题型
    for etype in existing_types:
        if etype not in all_types:
            all_types.append(etype)
    
    return all_types


def fetch_qids_by_bid(bank_id: int) -> Dict[str, int]:
    """
    获取指定题库下所有题目的id到order的映射关系

    Args:
        bank_id (int): 题库ID

    Returns:
        Dict[str, int]: 字典，键为question_id（字符串），值为order（题号）
    """
    conn = get_db()
    c = conn.cursor()

    try:
        c.execute('''
            SELECT id, "order"
            FROM questions
            WHERE bank_id = ?
            ORDER BY "order" ASC
        ''', (bank_id,))

        rows = c.fetchall()
        result = {}
        for row in rows:
            result[str(row['id'])] = row['order']

        return result

    except Exception as e:
        db_logger.error(f"获取题库{bank_id}题目映射失败: {e}")
        return {}


def get_wrong_question_ids(user_id: int) -> List[int]:
    """
    获取用户在所有题库中的错题ID列表，按最后错误时间倒序排列

    Args:
        user_id (int): 用户ID

    Returns:
        List[int]: 错题ID列表
    """
    conn = get_db()
    c = conn.cursor()

    try:
        c.execute('''
            SELECT question_id
            FROM history
            WHERE user_id = ?
              AND correct = 0
            ORDER BY updated_at DESC
        ''', (user_id,))

        rows = c.fetchall()
        return [row['question_id'] for row in rows]

    except Exception as e:
        db_logger.error(f"获取用户{user_id}错题ID列表失败: {e}")
        return []


def get_favorite_question_ids(user_id: int) -> List[int]:
    """
    获取用户在所有题库中的收藏题目ID列表，按收藏时间倒序排列

    Args:
        user_id (int): 用户ID

    Returns:
        List[int]: 收藏题目ID列表
    """
    conn = get_db()
    c = conn.cursor()

    try:
        c.execute('''
            SELECT question_id
            FROM favorites
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))

        rows = c.fetchall()
        return [row['question_id'] for row in rows]

    except Exception as e:
        db_logger.error(f"获取用户{user_id}收藏题目ID列表失败: {e}")
        return []