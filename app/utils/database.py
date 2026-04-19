"""
examcat - 数据库辅助函数
"""
import sqlite3
import os
import logging
import time
from typing import Dict, Union
from flask import g

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

def init_db():
    """
    初始化数据库
    """
    conn = get_db()
    c = conn.cursor()
    
    # 1. users 表
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. banks 表
    c.execute('''
        CREATE TABLE IF NOT EXISTS banks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bankname TEXT NOT NULL,
            type TEXT,
            category TEXT,
            total_count INTEGER NOT NULL DEFAULT 0,
            category_count TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(bankname)
        )
    ''')
    
    # 3. questions 表
    c.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            "order" INTEGER NOT NULL DEFAULT 0,
            bank_id INTEGER NOT NULL,
            stem TEXT NOT NULL,
            answer TEXT NOT NULL,
            type TEXT,
            type2 TEXT,
            category TEXT,
            options TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (bank_id) REFERENCES banks(id)
        )
    ''')
    # 创建索引：加速查询“某题库的题目顺序”
    c.execute('''
        CREATE INDEX IF NOT EXISTS 
            idx_questions_bank_order 
            ON questions (bank_id, "order")
    ''')
    
    # 4. history 表（新结构 - 聚合统计）
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            bank_id INTEGER NOT NULL,
            complete BOOLEAN DEFAULT 0,
            last_answer TEXT,
            correct BOOLEAN DEFAULT 0,
            correct_count INTEGER NOT NULL DEFAULT 0,
            wrong_count INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (question_id) REFERENCES questions(id),
            FOREIGN KEY (bank_id) REFERENCES banks(id),
            UNIQUE(user_id, question_id)
        )
    ''')
    # 创建索引：加速查询“某用户在某题库中已完成的题目”
    c.execute('''
        CREATE INDEX IF NOT EXISTS 
            idx_history_user_bank_complete
            ON history (user_id, bank_id, complete)
    ''')
    
    # 5. favorites 表
    c.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            bank_id INTEGER NOT NULL,
            tag TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (question_id) REFERENCES questions(id),
            FOREIGN KEY (bank_id) REFERENCES banks(id),
            UNIQUE(user_id, question_id)
        )
    ''')
    
    # 6. exams 表
    c.execute('''
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_ids TEXT NOT NULL,
            bank_id INTEGER NOT NULL,
            duration INTEGER NOT NULL,
            answers TEXT,
            complete BOOLEAN DEFAULT 0,
            score REAL,
            start_at DATETIME NOT NULL,
            restart_at DATETIME,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (bank_id) REFERENCES banks(id)
        )
    ''')
    # 添加索引：加速查询“用户最后一次未完成的考试”
    c.execute('''
        CREATE INDEX IF NOT EXISTS 
            idx_exam_user_complete_restart 
            ON exams (user_id, complete, restart_at)
    ''')

    # 7. question_stats 表
    c.execute('''
        CREATE TABLE IF NOT EXISTS question_stats (
            id INTEGER PRIMARY KEY,
            complete_count INTEGER NOT NULL DEFAULT 0,
            correct_count INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (id) REFERENCES questions(id)
        )
    ''')
    
    conn.commit()

# ========== history表 ===========
def add_history_record(user_id: int, question_id: int, user_answer: str, correct: int, bank_id: int) -> None:
    """
    添加答题历史记录
    
    Args:
        user_id (int): 用户ID
        question_id (int): 题目ID
        user_answer (str): 用户答案
        correct (int): 是否正确 (0/1)
        bank_id (int): 题库ID
    """
    conn = get_db()
    c = conn.cursor()
    
    try:
        # 检查记录是否存在
        c.execute('''
            SELECT id, correct_count, wrong_count 
            FROM history 
            WHERE user_id = ? AND question_id = ?
        ''', (user_id, question_id))
        
        existing_record = c.fetchone()
        
        if existing_record:
            # 更新现有记录
            record_id = existing_record['id']
            current_correct_count = existing_record['correct_count']
            current_wrong_count = existing_record['wrong_count']
            
            # 计算增量
            delta_correct = 1 if correct else 0
            delta_wrong = 0 if correct else 1
            
            # 更新统计计数
            new_correct_count = current_correct_count + delta_correct
            new_wrong_count = current_wrong_count + delta_wrong
            
            c.execute('''
                UPDATE history 
                SET last_answer = ?, 
                    correct = ?,
                    correct_count = ?,
                    wrong_count = ?,
                    updated_at = CURRENT_TIMESTAMP,
                    complete = 1
                WHERE id = ?
            ''', (user_answer, bool(correct), new_correct_count, new_wrong_count, record_id))
            
            # 增量更新题目统计
            # delta_complete = 1（每次答题增加一次完成）
            update_question_stats(question_id, delta_complete=1, delta_correct=delta_correct)
            
            db_logger.info(f"[{os.getpid()}] update_history_record: 用户{user_id}, 题目{question_id}, 答案{user_answer}, 正确{correct}, 题库ID{bank_id}")
        else:
            # 插入新记录
            correct_count = 1 if correct else 0
            wrong_count = 0 if correct else 1
            
            c.execute('''
                INSERT INTO history (
                    user_id, question_id, bank_id, complete,
                    last_answer, correct, correct_count, wrong_count,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (
                user_id, question_id, bank_id, 1,
                user_answer, bool(correct), correct_count, wrong_count
            ))
            
            # 增量更新题目统计
            # 第一次答题：delta_complete=1, delta_correct=1或0
            update_question_stats(question_id, delta_complete=1, delta_correct=correct_count)
            
            db_logger.info(f"[{os.getpid()}] add_history_record: 用户{user_id}, 题目{question_id}, 答案{user_answer}, 正确{correct}, 题库ID{bank_id}")
        
        conn.commit()
        
    except Exception as e:
        print(f"Error adding/updating history record: {e}")
        db_logger.error(f"[{os.getpid()}] add_history_record: 用户{user_id}, 题目{question_id}, 错误: {str(e)}")
        conn.rollback()
        raise

def reset_history_record(user_id: int, bank_id: int) -> None:
    """
    重置用户在指定题库的答题记录，只将complete设为0
    
    Args:
        user_id (int): 用户ID
        bank_id (int): 题库ID
        
    Returns:
        int: 重置的记录数
    """
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute('''
            UPDATE history 
            SET complete = 0,
                last_answer = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND bank_id = ? AND complete = 1
        ''', (user_id, bank_id))
        
        updated_count = c.rowcount
        conn.commit()        
        db_logger.info(f"重置用户 {user_id} 在题库 {bank_id} 的答题记录: {updated_count} 条记录已重置")

        return updated_count
        
    except Exception as e:
        db_logger.error(f"重置答题记录失败，用户 {user_id}，题库 {bank_id}: {e}")
        conn.rollback()
        raise

# ========== question_stats表 ===========
def update_question_stats(question_id: int, delta_complete: int = 0, delta_correct: int = 0) -> None:
    """
    增量更新题目统计信息
    
    Args:
        question_id (int): 题目ID
        delta_complete (int): 完成次数增量（默认0）
        delta_correct (int): 正确次数增量（默认0）
    """
    conn = get_db()
    c = conn.cursor()
    
    try:
        # 1. 检查记录是否存在
        c.execute('SELECT id FROM question_stats WHERE id = ?', (question_id,))
        existing_record = c.fetchone()
        
        if existing_record:
            # 2. 记录存在：执行增量更新
            c.execute('''
                UPDATE question_stats 
                SET complete_count = complete_count + ?,
                    correct_count = correct_count + ?
                WHERE id = ?
            ''', (delta_complete, delta_correct, question_id))
            
            # # 获取更新后的值用于日志
            # c.execute('SELECT complete_count, correct_count FROM question_stats WHERE id = ?', (question_id,))
            # updated_row = c.fetchone()
            
            # if updated_row:
            #     logger.debug(f"增量更新题目 {question_id}: complete={updated_row['complete_count']}, correct={updated_row['correct_count']}")
            # else:
            #     logger.warning(f"题目 {question_id} 更新后查询失败")
            
        else:
            # 3. 记录不存在：从history表聚合统计创建新记录
            c.execute('''
                SELECT 
                    SUM(correct_count + wrong_count) as complete_count,
                    SUM(correct_count) as correct_count
                FROM history
                WHERE question_id = ?
            ''', (question_id,))
            
            stats = c.fetchone()
            
            if stats:
                base_complete = stats['complete_count'] or 0
                base_correct = stats['correct_count'] or 0
                
                # 加上增量值
                total_complete = base_complete + delta_complete
                total_correct = base_correct + delta_correct
                
                c.execute('''
                    INSERT INTO question_stats (id, complete_count, correct_count)
                    VALUES (?, ?, ?)
                ''', (question_id, total_complete, total_correct))
                
                # logger.debug(f"创建题目 {question_id} 统计: complete={total_complete}, correct={total_correct}")
            else:
                # 如果history表中也没有记录，使用增量值创建新记录
                c.execute('''
                    INSERT INTO question_stats (id, complete_count, correct_count)
                    VALUES (?, ?, ?)
                ''', (question_id, delta_complete, delta_correct))
                
                # logger.debug(f"创建题目 {question_id} 统计（无历史记录）: complete={delta_complete}, correct={delta_correct}")
        
        conn.commit()
            
    except Exception as e:
        db_logger.error(f"更新题目统计失败，题目ID: {question_id}, 错误: {e}")
        conn.rollback()
        raise

def fetch_question_stats(question_id: int) -> Dict[str, Union[int, float]]:
    """
    获取题目的答题统计信息
    
    Args:
        question_id (int): 题目ID
        
    Returns:
        dict: 包含统计信息的字典，格式为：
            {
                'total_answered': int,   # 总答题次数
                'total_correct': int,    # 正确答题次数
                'accuracy': float        # 正确率(0-100)
            }
    
    Example:
        >>> stats = fetch_question_stats(123)
        >>> print(f"正确率 {stats['accuracy']}%")
        正确率 75.5%
    """
    conn = get_db()
    c = conn.cursor()
    
    try:
        # 从question_stats表获取统计信息
        c.execute('''
            SELECT complete_count, correct_count
            FROM question_stats
            WHERE id = ?
        ''', (question_id,))
        
        stats_row = c.fetchone()
        
        if stats_row:
            total_answered = stats_row['complete_count']
            total_correct = stats_row['correct_count']

        else:
            # 如果没有统计记录，从history表聚合
            c.execute('''
                SELECT 
                    SUM(correct_count + wrong_count) as total_answered,
                    SUM(correct_count) as total_correct
                FROM history
                WHERE question_id = ?
            ''', (question_id,))
            
            history_row = c.fetchone()
            
            if history_row and history_row['total_answered']:
                total_answered = history_row['total_answered']
                total_correct = history_row['total_correct'] if history_row['total_correct'] else 0
            else:
                total_answered = 0
                total_correct = 0
        
        # 计算正确率（百分比，保留1位小数）
        accuracy = round((total_correct / total_answered) * 100, 1) if total_answered > 0 else 0.0
        
        return {
            'total_answered': total_answered,
            'total_correct': total_correct,
            'accuracy': accuracy
        }
            
    except Exception as e:
        db_logger.error(f"Error getting question stats for {question_id}: {e}")
        # 发生错误时返回默认值
        return {
            'total_answered': 0,
            'total_correct': 0,
            'accuracy': 0.0
        }

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