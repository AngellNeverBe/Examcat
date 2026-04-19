"""
examcat - 题库辅助函数
"""
import json
import os
import time
import glob
import csv
from flask import request
from typing import Dict, Union, List, Tuple, Optional, Any
from .cookie import cookie_logger
from .database import get_db, db_logger

# ======== 核心操作 ========
def fetch_bank(bank_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetch a bank by ID from the database.
    
    Args:
        bank_id (int): The bank ID
        
    Returns:
        dict: The bank data or None if not found
    """
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM banks WHERE id=?', (bank_id,))
    row = c.fetchone()
    
    if row:
        # 解析category_count
        category_count = {}
        if row['category_count']:
            try:
                category_count = json.loads(row['category_count'])
            except json.JSONDecodeError:
                category_count = {}
        
        return {
            'id': row['id'],
            'bankname': row['bankname'],
            'type': row['type'],
            'category': row['category'],
            'total_count': row['total_count'],
            'category_count': category_count,
            'created_at': row['created_at']
        }
    return None

def fetch_all_banks(user_id: int) -> List[Dict[str, Any]]:
    """
    获取所有题库及其用户答题统计信息

    Args:
        user_id (int): 用户ID

    Returns:
        list[dict]: 题库字典列表，每个字典包含以下字段：
            - id: 题库ID
            - name: 题库名称
            - type: 题库类型
            - category: 题库分类（标准化后）
            - total: 题目总数
            - answered: 已答题目数
            - correct: 答对题目数
            - wrong: 答错题目数
            - category_count: 分类统计字典（解析自category_count JSON）

    Note:
        - 分类名称标准化：如果不在 ['大一','大二','大三','大四','大五','其他'] 中，则归为'其他'
        - category_count 字段已从JSON字符串解析为字典
    """
    conn = get_db()
    c = conn.cursor()

    c.execute('''
        SELECT
            b.id,
            b.bankname,
            b.type,
            b.category,
            b.total_count,
            b.category_count,
            COALESCE(SUM(CASE WHEN h.complete = 1 THEN 1 ELSE 0 END), 0) as answered_count,
            COALESCE(SUM(CASE WHEN h.complete = 1 AND h.correct = 1 THEN 1 ELSE 0 END), 0) as correct_count,
            COALESCE(SUM(CASE WHEN h.complete = 1 AND h.correct = 0 THEN 1 ELSE 0 END), 0) as wrong_count
        FROM banks b
        LEFT JOIN history h ON b.id = h.bank_id AND h.user_id = ?
        GROUP BY b.id, b.bankname, b.type, b.category, b.total_count, b.category_count
        ORDER BY b.category, b.bankname
    ''', (user_id,))

    all_categories = ['大一', '大二', '大三', '大四', '大五', '其他']
    banks = []

    for row in c.fetchall():
        # 解析category_count
        category_count = {}
        if row['category_count']:
            try:
                category_count = json.loads(row['category_count'])
            except:
                category_count = {}

        # 标准化分类名称
        bank_category = row['category'] or '其他'
        if bank_category not in all_categories:
            bank_category = '其他'

        banks.append({
            'id': row['id'],
            'name': row['bankname'],
            'type': row['type'],
            'category': bank_category,
            'total': row['total_count'] or 0,
            'answered': row['answered_count'] or 0,
            'correct': row['correct_count'] or 0,
            'wrong': row['wrong_count'] or 0,
            'category_count': category_count
        })

    return banks

def get_current_bank_id(user_id: int) -> Tuple[Optional[int], Dict[str, str]]:
    """
    获取用户的当前题库ID，优先使用cookie缓存
    
    Args:
        user_id (int): 用户ID
        
    Returns:
        tuple: (bank_id, cookie_dict) 
               bank_id: 当前题库ID，如果没有返回None
               cookie_dict: 需要设置的cookie字典，如果为空表示cookie已存在
    """
    cookie_key = 'current_bank_id'
    
    try:
        # 尝试从cookie获取
        if request and hasattr(request, 'cookies'):
            cookie_value = request.cookies.get(cookie_key)
            if cookie_value and cookie_value.isdigit():
                bank_id = int(cookie_value)
                cookie_logger.debug(f"从cookie获取用户 {user_id} 当前题库ID: {bank_id}")
                return bank_id, {}  # 返回数据和空cookie字典
    except Exception as e:
        cookie_logger.debug(f"读取cookie失败: {e}")
        pass
    
    # 从数据库获取
    conn = get_db()
    c = conn.cursor()
    try:
        # 获取用户最后一次答题的bank_id
        c.execute('''
            SELECT bank_id 
            FROM history 
            WHERE user_id = ? 
            ORDER BY updated_at DESC 
            LIMIT 1
        ''', (user_id,))
        
        row = c.fetchone()
        if row:
            bank_id = row['bank_id']
        else:
            # 如果没有历史记录，返回第一个题库的ID
            c.execute('SELECT id FROM banks ORDER BY id ASC LIMIT 1')
            row = c.fetchone()
            bank_id = row['id'] if row else None
        
        if bank_id:
            # 返回数据和需要设置的cookie
            cookie_logger.debug(f"从数据库获取用户 {user_id} 当前题库ID: {bank_id}")
            return bank_id, {cookie_key: str(bank_id)}
        else:
            cookie_logger.warning(f"用户 {user_id} 没有可用题库")
            return None, {}
            
    except Exception as e:
        cookie_logger.error(f"获取用户 {user_id} 当前题库失败: {e}")
        return None, {}

def add_bank(csv_file_path: str, bankname: Optional[str] = None, type: Optional[str] = None, category: Optional[str] = None) -> Optional[int]:
    """
    新增题库信息到banks表，并将题目导入数据库
    
    Args:
        csv_file_path (str): CSV文件路径
        bankname (str): 题库名称，如果为None则从文件名获取
        type (str): 题库类型，可以为空
        category (str): 题库分类，可以为空
        
    Returns:
        int: 新题库的bank_id
    """
    conn = get_db()
    c = conn.cursor()
    
    try:
        # 如果未提供bankname，从文件名获取
        if bankname is None:
            file_name = os.path.basename(csv_file_path)
            bankname = os.path.splitext(file_name)[0]
        
        # 检查是否已存在相同名称的题库
        c.execute('SELECT id FROM banks WHERE bankname = ?', (bankname,))
        if c.fetchone():
            raise ValueError(f"题库 '{bankname}' 已存在")
        
        # 读取CSV文件统计信息
        with open(csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            total_count = len(rows)
            
            # 统计类别分布
            category_stats = {}
            for row in rows:
                cat = row.get('类别', '未分类')
                if not cat:
                    cat = '未分类'
                category_stats[cat] = category_stats.get(cat, 0) + 1
            
            # 将统计字典转为JSON字符串
            category_count_json = json.dumps(category_stats, ensure_ascii=False)
            
            # 插入banks表
            c.execute('''
                INSERT INTO banks (bankname, type, category, total_count, category_count)
                VALUES (?, ?, ?, ?, ?)
            ''', (bankname, type, category, total_count, category_count_json))
            
            bank_id = c.lastrowid
            
            # 导入题目到questions表
            for order, row in enumerate(rows, 1):
                options = {}
                for opt in ['A', 'B', 'C', 'D', 'E']:
                    if row.get(opt) and row[opt].strip():
                        options[opt] = row[opt]
                
                # 获取CSV字段，适配新旧字段名
                stem = row.get("题干", row.get("题目", ""))
                answer = row.get("答案", "")
                type = row.get("题型", row.get("类型", "未知"))
                type2 = row.get("次要题型", "")  # type2字段
                category = row.get("类别", "未分类")
                
                c.execute('''
                    INSERT INTO questions ("order", bank_id, stem, answer, type, type2, category, options)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    order, bank_id, stem, answer, type, type2, category,
                    json.dumps(options, ensure_ascii=False)
                ))
            
            conn.commit()
            db_logger.info(f"成功添加题库: {bankname} (ID: {bank_id}), 题目数: {total_count}")
            return bank_id
            
    except Exception as e:
        conn.rollback()
        db_logger.error(f"添加题库失败: {e}")
        raise

def load_bank() -> Dict[str, Union[int, List[str]]]:
    """
    刷新题库：扫描 CSV 文件夹，新增不在 banks 表中的题库。

    该函数会扫描 `./questions-bank` 目录下的所有 CSV 文件，与数据库 `banks` 表中的题库名称进行比对，
    将新发现的题库添加到数据库，同时检查数据库中已存在的题库对应的 CSV 文件是否仍然存在，并记录错误信息。

    Returns:
        dict: 包含三个键的字典：
            - `added` (int): 成功新增的题库数量。
            - `errors` (List[str]): 加载过程中发生的错误列表，每个元素为描述错误信息的字符串。
            - `missing_csv` (List[str]): 数据库中已存在但 CSV 文件缺失的题库列表，每个元素为描述问题的字符串。

    Side Effects:
        - 若 `./questions-bank` 目录不存在，则会创建该目录。
        - 会向数据库 `banks` 表插入新题库记录（通过调用 `add_bank`）。
        - 会通过 `db_logger` 记录信息及错误日志。

    Note:
        - 仅当 CSV 文件的题库名不在数据库中时才添加，不会更新已存在的题库。
        - 如果 `add_bank` 内部对 CSV 格式有要求，该函数将捕获其异常并记录。
    """
    banks_dir = './questions-bank'
    if not os.path.exists(banks_dir):
        os.makedirs(banks_dir, exist_ok=True)
    
    # 获取所有CSV文件
    csv_files = glob.glob(os.path.join(banks_dir, '*.csv'))
    
    # 获取数据库中已存在的题库名称
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT bankname FROM banks')
    existing_banks = {row['bankname'] for row in c.fetchall()}
    
    result: Dict[str, Union[int, List[str]]] = {
        'added': 0,
        'errors': [],
        'missing_csv': []
    }
    
    # 检查banks表中存在但CSV文件不存在的题库
    for bankname in existing_banks:
        csv_path = os.path.join(banks_dir, f"{bankname}.csv")
        if not os.path.exists(csv_path):
            error_msg = f"题库 '{bankname}' 在数据库中存在，但CSV文件不存在或已移动"
            db_logger.error(error_msg)
            result['missing_csv'].append(error_msg)
    
    # 新增不在数据库中的题库
    for csv_file in csv_files:
        bankname = os.path.splitext(os.path.basename(csv_file))[0]
        
        if bankname not in existing_banks:
            try:
                bank_id = add_bank(csv_file, bankname)
                result['added'] += 1
                db_logger.info(f"成功加载题库: {bankname} (ID: {bank_id})")
            except Exception as e:
                error_msg = f"加载题库 '{bankname}' 失败: {str(e)}"
                db_logger.error(error_msg)
                result['errors'].append(error_msg)
    
    return result

# ======== 修改操作 ========
def update_bank(bank_id: int, bankname: Optional[str] = None, type: Optional[str] = None, category: Optional[str] = None) -> bool:
    """
    更新题库基本信息（同步重命名CSV文件）

    Args:
        bank_id (int): 题库ID
        bankname (str): 新的题库名称，如果为None则不更新
        type (str): 新的题库类型，如果为None则不更新
        category (str): 新的题库分类，如果为None则不更新

    Returns:
        bool: 是否成功更新
    """
    conn = get_db()
    c = conn.cursor()

    try:
        # 获取旧名称（仅在需要更新名称时）
        old_bankname = None
        if bankname is not None:
            c.execute('SELECT bankname FROM banks WHERE id = ?', (bank_id,))
            row = c.fetchone()
            if row:
                old_bankname = row['bankname']

        # 构建更新字段
        update_fields = []
        params = []

        if bankname is not None:
            # 检查新名称是否已存在（排除自身）
            c.execute('SELECT id FROM banks WHERE bankname = ? AND id != ?', (bankname, bank_id))
            if c.fetchone():
                raise ValueError(f"题库名称 '{bankname}' 已被使用")
            update_fields.append("bankname = ?")
            params.append(bankname)

        if type is not None:
            update_fields.append("type = ?")
            params.append(type)

        if category is not None:
            update_fields.append("category = ?")
            params.append(category)

        if not update_fields:
            return True  # 没有需要更新的字段

        params.append(bank_id)

        # 执行数据库更新
        sql = f"UPDATE banks SET {', '.join(update_fields)} WHERE id = ?"
        c.execute(sql, params)

        # 如果名称发生变化，先尝试重命名CSV文件（在commit前）
        if bankname is not None and old_bankname is not None and old_bankname != bankname:
            if not update_bank_in_csv(old_bankname, bankname):
                raise Exception(f"Failed to rename CSV file from '{old_bankname}.csv' to '{bankname}.csv'")

        conn.commit()

        if c.rowcount > 0:
            db_logger.info(f"更新题库 ID {bank_id} 成功")
            return True
        else:
            db_logger.warning(f"未找到题库 ID {bank_id}")
            return False

    except Exception as e:
        conn.rollback()
        db_logger.error(f"更新题库失败: {e}")
        raise

def update_bank_in_csv(old_bankname: str, new_bankname: str) -> bool:
    """
    重命名题库对应的CSV文件

    Args:
        old_bankname (str): 旧的题库名称
        new_bankname (str): 新的题库名称

    Returns:
        bool: 是否成功重命名
    """
    old_path = os.path.join('./questions-bank', f"{old_bankname}.csv")
    new_path = os.path.join('./questions-bank', f"{new_bankname}.csv")

    # 如果旧文件不存在，可能是题库尚未创建CSV文件，直接返回成功
    if not os.path.exists(old_path):
        db_logger.info(f"CSV file for old bank '{old_bankname}' not found, skipping rename")
        return True

    # 检查新文件名是否已存在，避免覆盖
    if os.path.exists(new_path):
        db_logger.error(f"Cannot rename: CSV file for new bank '{new_bankname}' already exists")
        return False

    try:
        os.rename(old_path, new_path)
        db_logger.info(f"Renamed CSV file from '{old_bankname}.csv' to '{new_bankname}.csv'")
        return True
    except Exception as e:
        db_logger.error(f"Failed to rename CSV file: {e}")
        return False

def switch_current_bank(user_id: int, bank_id: int) -> Dict[str, str]:
    """
    切换用户当前题库，返回需要设置的cookie字典
    
    注意：这里不使用get_current_sequential_question_id，因为它可能从cookie读取旧的current_bank_id
    而是直接获取新题库的第一个题目ID作为current_seq_qid
    
    Args:
        user_id (int): 用户ID
        bank_id (int): 新的题库ID
        
    Returns:
        Dict[str, str]: 需要设置的cookie字典
    """
    from .cookie import cookie_logger
    
    cookie_logger.info(f"[switch_current_bank] 用户 {user_id} 切换到题库 {bank_id}")
    
    # 检查题库是否存在
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id FROM banks WHERE id = ?', (bank_id,))
    if not c.fetchone():
        raise ValueError(f"题库 {bank_id} 不存在")
    
    # 设置当前题库ID的cookie
    cookies = {'current_bank_id': str(bank_id)}
    
    # # 获取新题库的第一个题目ID
    # first_qid = get_first_question_id(bank_id)
    # if first_qid:
    #     cookies['current_seq_qid'] = str(first_qid)
    #     cookie_logger.info(f"[switch_current_bank] 设置 current_seq_qid={first_qid}")
    # else:
    #     cookie_logger.warning(f"[switch_current_bank] 题库 {bank_id} 没有题目")
    
    return cookies