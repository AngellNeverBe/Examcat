"""
examcat - 数据库辅助函数
"""
import sqlite3
import json
import os
import glob
import csv
import logging
import time
from functools import wraps
from flask import session, request, redirect, url_for, flash, g

def get_db():
    """
    Create a database connection and configure it to return rows as dictionaries.
    
    Returns:
        sqlite3.Connection: The configured database connection
    """
    if 'db' not in g:
        
        g.db = sqlite3.connect('database.db', timeout=20.0)
        g.db.row_factory = sqlite3.Row
        
        g.db.execute('PRAGMA journal_mode=WAL;')      # WAL模式
        g.db.execute('PRAGMA busy_timeout = 5000;')   # 超时等待5秒
        g.db.execute('PRAGMA synchronous = NORMAL;')  # 平衡速度和安全
        g.db.execute('PRAGMA cache_size = -10000;')   # 10MB内存缓存

        # db_logger.info(f"[{os.getpid()}] Connect db.")
    
    return g.db

def close_db(e=None):
    """
    请求结束后的数据库自动关闭
    """
    db = g.pop('db', None)
    if db is not None:

        db.close()
        # db_logger.info(f"[{os.getpid()}] Connection closed.")

def init_app(app):
    """
    上下文处理
    """
    app.teardown_appcontext(close_db)

def migrate_database():
    """
    Migrate the database to add new columns if they don't exist.
    This handles database schema updates without losing data.
    """
    conn = get_db()
    c = conn.cursor()
    
    # Check if current_bank column exists in users table
    try:
        c.execute('SELECT current_bank FROM users LIMIT 1')
    except sqlite3.OperationalError:
        # Column doesn't exist, add it
        print("Adding current_bank column to users table...")
        c.execute('ALTER TABLE users ADD COLUMN current_bank TEXT DEFAULT "questions"')  # 修改：去掉.csv后缀
    
    # Check if bank_name column exists in questions table
    try:
        c.execute('SELECT bank_name FROM questions LIMIT 1')
    except sqlite3.OperationalError:
        # Column doesn't exist, add it
        print("Adding bank_name column to questions table...")
        c.execute('ALTER TABLE questions ADD COLUMN bank_name TEXT DEFAULT "questions"')  # 修改：去掉.csv后缀
        
        # Update existing questions to have the default bank name
        c.execute('UPDATE questions SET bank_name = "questions" WHERE bank_name IS NULL')
    
    # Check if bank_name column exists in history table
    try:
        c.execute('SELECT bank_name FROM history LIMIT 1')
    except sqlite3.OperationalError:
        # Column doesn't exist, add it
        print("Adding bank_name column to history table...")
        c.execute('ALTER TABLE history ADD COLUMN bank_name TEXT')
    
    conn.commit()
    
    
    # Migrate existing history records to have bank_name
    migrate_history_data()

def migrate_history_data():
    """
    Migrate existing history records to populate the bank_name field.
    This should be called after adding the bank_name column to history table.
    """
    conn = get_db()
    c = conn.cursor()
    
    try:
        # Update existing history records with bank_name from questions table
        c.execute('''
            UPDATE history 
            SET bank_name = (
                SELECT bank_name FROM questions 
                WHERE questions.id = history.question_id
                LIMIT 1
            )
            WHERE bank_name IS NULL
        ''')
        
        updated_count = c.rowcount
        if updated_count > 0:
            print(f"Migrated {updated_count} history records with bank_name")
        
        conn.commit()
    except Exception as e:
        print(f"Error migrating history data: {e}")
        conn.rollback()

def init_db():
    """
    Initialize the database by creating necessary tables if they don't exist.
    """
    conn = get_db()
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        current_seq_qid TEXT,
        current_bank TEXT DEFAULT 'questions',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # History table for tracking user answers - UPDATED with bank_name
    c.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        question_id TEXT NOT NULL,
        user_answer TEXT NOT NULL,
        correct INTEGER NOT NULL,
        bank_name TEXT, -- 记录题目所属题库
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    # Questions table for storing question data
    c.execute('''CREATE TABLE IF NOT EXISTS questions (
        id TEXT PRIMARY KEY,
        stem TEXT NOT NULL,
        answer TEXT NOT NULL,
        difficulty TEXT,
        qtype TEXT,
        category TEXT,
        options TEXT, -- JSON stored options
        bank_name TEXT DEFAULT 'questions',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Favorites table for user bookmarks
    c.execute('''CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        question_id TEXT NOT NULL,
        tag TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, question_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (question_id) REFERENCES questions(id)
    )''')
    
    # Exam sessions table for timed mode and exams
    c.execute('''CREATE TABLE IF NOT EXISTS exam_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        mode TEXT NOT NULL, -- 'exam' or 'timed'
        question_ids TEXT NOT NULL, -- JSON list
        start_time DATETIME NOT NULL,
        duration INTEGER NOT NULL, -- seconds
        completed BOOLEAN DEFAULT 0,
        score REAL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    conn.commit()
    
    
    # Run database migration to add new columns if needed
    migrate_database()

def add_history_record(user_id, question_id, user_answer, correct, bank_name):
    """
    添加答题历史记录，包含题库信息。
    
    Args:
        user_id (int): 用户ID
        question_id (str): 题目ID
        user_answer (str): 用户答案
        correct (int): 是否正确 (0/1)
        bank_name (str): 题库名称（不带.csv后缀）
    """
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute(
            'INSERT INTO history (user_id, question_id, user_answer, correct, bank_name) VALUES (?,?,?,?,?)',
            (user_id, question_id, user_answer, correct, bank_name)
        )
        conn.commit()
        db_logger.info(f"[{os.getpid()}] add_history_record: 用户{user_id}, 题目{question_id}, 答案{user_answer}, 正确{correct}, 题库{bank_name}")
    except Exception as e:
        print(f"Error adding history record: {e}")
        db_logger.error(f"[{os.getpid()}] add_history_record: 用户{user_id}, 题目{question_id}, 错误: {str(e)}")
        conn.rollback()
        raise
        

def get_available_banks():
    """
    Get all available question banks (CSV files) from the questions-bank directory.
    
    Returns:
        list: List of CSV filenames in the questions-bank directory（不带.csv后缀）
    """
    banks_dir = './questions-bank'
    if not os.path.exists(banks_dir):
        os.makedirs(banks_dir, exist_ok=True)
    
    # Get all CSV files in the directory
    csv_files = glob.glob(os.path.join(banks_dir, '*.csv'))
    
    # Extract just the filenames and remove .csv suffix
    banks = [os.path.splitext(os.path.basename(f))[0] for f in csv_files]
    
    # If no CSV files found, create a sample one
    if not banks:
        default_bank = 'sample_questions'
        default_path = os.path.join(banks_dir, default_bank + '.csv')
        # Create a sample CSV file
        with open(default_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['题号', '题干', '答案', '难度', '题型', '类别', 'A', 'B', 'C', 'D', 'E'])
            writer.writerow(['1', '这是一个示例题目', 'A', '简单', '单选题', '示例', '正确选项', '错误选项', '错误选项', '错误选项', ''])
        banks.append(default_bank)
    
    return sorted(banks)

def get_first_bank():
    """
    Get the first question bank from questions-bank folder.
    
    Returns:
        str: The first question bank filename（不带.csv后缀）, or None if none exist
    """
    banks = get_available_banks()
    return banks[0] if banks else None

def get_current_bank(user_id):
    """
    Get the current question bank for a user.
    
    Args:
        user_id (int): The user ID
        
    Returns:
        str: The current question bank filename（不带.csv后缀）
    """
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT current_bank FROM users WHERE id = ?', (user_id,))
    row = c.fetchone()
    
    
    if row and row['current_bank']:
        # Check if the bank exists in questions-bank folder
        bank_name = row['current_bank']
        banks = get_available_banks()
        if bank_name in banks:
            return bank_name
        
        # If bank doesn't exist, get first available bank
        first_bank = get_first_bank()
        if first_bank:
            # Update user's current bank
            set_current_bank(user_id, first_bank)
            return first_bank
    
    # Get first bank or default
    first_bank = get_first_bank()
    return first_bank if first_bank else 'questions'

def set_current_bank(user_id, bank_name):
    """
    设置用户的当前题库，并更新当前题目ID。
    
    Args:
        user_id (int): 用户ID
        bank_name (str): 题库名称（可以带或不带.csv后缀）
    """
    # 确保bank_name不带.csv后缀
    if bank_name.endswith('.csv'):
        bank_name = bank_name[:-4]  # 去掉.csv后缀
    
    conn = get_db()
    c = conn.cursor()
    
    # 更新当前题库
    c.execute('UPDATE users SET current_bank = ? WHERE id = ?', (bank_name, user_id))
    # 为新题库计算新的当前题目ID
    next_qid = get_next_question_id(conn, user_id, bank_name)
    if next_qid:
        c.execute('UPDATE users SET current_seq_qid = ? WHERE id = ?', (next_qid, user_id))
    
    conn.commit()
    

def load_questions_to_db(conn, bank_name):
    """
    Load questions from a CSV file into the database.
    
    Args:
        conn (sqlite3.Connection): The database connection
        bank_name (str): The question bank filename（可以带或不带.csv后缀）
    """
    try:
        # 确保bank_name有.csv后缀来查找文件
        if not bank_name.endswith('.csv'):
            file_name = bank_name + '.csv'
        else:
            file_name = bank_name
            bank_name = bank_name[:-4]  # 去掉.csv后缀存储
        
        bank_path = os.path.join('./questions-bank', file_name)
        
        # Check if file exists
        if not os.path.exists(bank_path):
            print(f"Warning: {bank_path} file not found. No questions loaded.")
            return
        
        with open(bank_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            c = conn.cursor()
            
            # Clear existing questions from this bank
            c.execute('DELETE FROM questions WHERE bank_name = ?', (bank_name,))
            
            for row in reader:
                options = {}
                for opt in ['A', 'B', 'C', 'D', 'E']:
                    if row.get(opt) and row[opt].strip():
                        options[opt] = row[opt]
                
                # 修复：为题目ID添加题库前缀，确保唯一性
                original_id = row.get('题号', '0')
                question_id = f"{bank_name}_{original_id}"  # 添加题库名前缀（不带.csv后缀）
                                
                c.execute(
                    "INSERT OR REPLACE INTO questions (id, stem, answer, difficulty, qtype, category, options, bank_name) VALUES (?,?,?,?,?,?,?,?)",
                    (
                        question_id,  # 使用带前缀的ID
                        row.get("题干", ""),
                        row.get("答案", ""),
                        row.get("难度", "未知"),
                        row.get("题型", "未知"),
                        row.get("类别", "未分类"),
                        json.dumps(options, ensure_ascii=False),
                        bank_name  # 存储不带.csv后缀的题库名
                    ),
                )
            conn.commit()
            print(f"Loaded {c.rowcount} questions from {bank_name}")
    except Exception as e:
        print(f"Error loading questions from {bank_name}: {e}")
        conn.rollback()

def load_all_banks():
    """
    Load questions from all available banks into the database.
    """
    conn = get_db()
    banks = get_available_banks()  # 获取不带后缀的题库名
    
    for bank in banks:
        load_questions_to_db(conn, bank)
    
    

def get_questions_by_bank(conn, bank_name):
    """
    Get all questions from a specific bank.
    
    Args:
        conn (sqlite3.Connection): The database connection
        bank_name (str): The question bank filename（不带.csv后缀）
        
    Returns:
        list: List of questions from the specified bank
    """
    c = conn.cursor()
    c.execute('SELECT * FROM questions WHERE bank_name = ?', (bank_name,))
    return c.fetchall()

def get_current_question_id(user_id):
    """
    获取用户当前题目ID，确保它属于当前题库。
    如果不属于，则重新计算并更新。
    """
    conn = get_db()
    c = conn.cursor()
    
    # 获取当前题库
    c.execute('SELECT current_bank, current_seq_qid FROM users WHERE id = ?', (user_id,))
    row = c.fetchone()
    if not row:
        print('yes')
        
        return None
    
    bank_name = row['current_bank']
    current_qid = row['current_seq_qid']
    
    
    # 如果current_qid为None，计算下一个题目
    if current_qid is None:
        next_qid = get_next_question_id(conn, user_id, bank_name)
        if next_qid:
            c.execute('UPDATE users SET current_seq_qid = ? WHERE id = ?', (next_qid, user_id))
            conn.commit()
        
        return next_qid
    
    # 检查current_qid是否属于当前题库
    c.execute('SELECT bank_name FROM questions WHERE id = ?', (current_qid,))
    q_row = c.fetchone()
    if q_row and q_row['bank_name'] == bank_name:
        # 当前题目ID有效
        
        return current_qid
    else:
        # 当前题目ID不属于当前题库，重新计算
        next_qid = get_next_question_id(conn, user_id, bank_name)
        if next_qid:
            c.execute('UPDATE users SET current_seq_qid = ? WHERE id = ?', (next_qid, user_id))
            conn.commit()
        
        return next_qid

def get_next_question_id(conn, user_id, bank_name):
    """获取用户在题库中下一个应该做的题号（按数字顺序）"""
    c = conn.cursor()
    
    # 获取当前题库所有题目ID
    c.execute('SELECT id FROM questions WHERE bank_name = ?', (bank_name,))
    all_questions = [row['id'] for row in c.fetchall()]
    
    # 获取用户已做题目ID（仅限当前题库）
    c.execute('''
        SELECT DISTINCT question_id 
        FROM history 
        WHERE user_id = ? AND bank_name = ?
    ''', (user_id, bank_name))
    answered_questions = [row['question_id'] for row in c.fetchall()]
    
    # 找出未做题目
    unanswered = [qid for qid in all_questions if qid not in answered_questions]
    
    if unanswered:
        # 按数字部分排序
        unanswered.sort(key=extract_qid_number)
        return unanswered[0]
    else:
        # 所有题目都已做，返回第一个题目
        if all_questions:
            all_questions.sort(key=extract_qid_number)
            return all_questions[0]
    
    return None

def get_bank_progress(user_id, bank_name):
    """获取用户在指定题库的完成进度"""
    conn = get_db()
    c = conn.cursor()
    
    # 获取题库总题数
    c.execute('SELECT COUNT(*) as total FROM questions WHERE bank_name = ?', (bank_name,))
    total_row = c.fetchone()
    total = total_row['total'] if total_row else 0
    
    # 获取用户已做题数 - 使用新的bank_name字段确保准确性
    c.execute('''
        SELECT COUNT(DISTINCT question_id) as answered
        FROM history 
        WHERE user_id = ? AND bank_name = ?
    ''', (user_id, bank_name))
    answered_row = c.fetchone()
    answered = answered_row['answered'] if answered_row else 0
    
    
    
    # 计算进度百分比
    progress = answered / total if total > 0 else 0
    
    return {
        'total': total,
        'answered': answered,
        'progress': round(progress * 100, 2)  # 转换为百分比，保留两位小数
    }

def extract_qid_number(qid):
    """
    从题目ID中提取数字部分。
    支持格式：bankname_qid 或 纯数字ID
    """
    if not qid:
        return 0
    
    # 从最后一个下划线后提取数字部分
    if '_' in qid:
        num_part = qid.rsplit('_', 1)[-1]
    else:
        num_part = qid
    
    try:
        return int(num_part)
    except ValueError:
        # 如果无法转换为数字，返回0确保排序在最后
        return 0

# ================= 数据库日志配置 =================
def setup_db_logger():
    """设置数据库专用日志记录器"""
    # 创建日志目录（如果不存在）
    log_dir = '/var/log/examcat'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # 创建数据库专用日志记录器
    db_logger = logging.getLogger('examcat.database')
    db_logger.setLevel(logging.INFO)  # 记录INFO及以上级别的日志
    
    # 避免重复添加处理器
    if not db_logger.handlers:
        # 创建文件处理器
        log_file = os.path.join(log_dir, 'database.log')
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # 添加到记录器
        db_logger.addHandler(file_handler)
    
    return db_logger
# 创建全局数据库日志记录器
db_logger = setup_db_logger()
# 简单的SQL执行计时装饰器
def log_sql_operation(func):
    """装饰器：记录SQL执行时间和结果"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = (time.time() - start_time) * 1000  # 转换为毫秒
            
            # 只记录耗时超过50ms的查询（避免日志太多）
            if duration > 50:
                # 提取SQL语句（如果是execute方法）
                sql = args[1] if len(args) > 1 else '未知SQL'
                db_logger.info(f"[{os.getpid()}] 慢查询: {sql[:100]}... 耗时: {duration:.2f}ms")
            
            return result
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            db_logger.error(f"SQL错误: {str(e)} 耗时: {duration:.2f}ms")
            raise e
    return wrapper
# ===============================================