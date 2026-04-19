"""
examcat - 考试辅助函数
"""
from datetime import datetime
from flask import json
from sqlite3 import Row
from typing import Optional
from .database import get_db
from .questions import fetch_question

# ======== 核心操作 ========
def fetch_exam(exam_id: int) -> Optional[Row]:
    """
    根据考试ID从数据库中获取完整的考试记录

    Args:
        exam_id (int): 要查询的考试记录的唯一标识 ID。

    Returns:
        Row (Optional[sqlite3.Row]): 
        如果找到考试记录，返回一个 `sqlite3.Row` 对象，包含以下字段：        
        - `id` (int): 考试记录 ID
        - `question_ids` (str): 逗号分隔的题目 ID 列表（如 ["12","34","56"]）
        - `duration` (int): 考试总时长（秒）
        - `answers` (str): 用户答案的 JSON 字符串
        - `complete` (int): 是否完成考试（0 未完成，1 已完成）
        - `score` (int): 最终得分（若未完成为 0）
        - `start_at` (str): 考试开始时间（ISO 格式时间戳）
        - `restart_at` (str): 恢复考试时的时间戳（初始值与 `start_at` 相等）
        
        如果不存在对应 ID 的考试记录，则返回 `None`。

    Examples:
        >>> exam = fetch_exam(1001)
        >>> if exam:
        ...     print(f"考试 ID: {exam['id']}, 开始时间: {exam['start_at']}")
        ... else:
        ...     print("考试记录不存在")

    Note:
        - 返回的 `sqlite3.Row` 对象支持字典式访问和索引访问。
        - 该函数不会修改数据库，仅执行 SELECT 查询。
    """
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT 
            id,
            question_ids,
            duration,
            answers,
            complete,
            score,
            start_at,
            restart_at
        FROM exams
        WHERE id = ?
    ''', (exam_id,))
    return c.fetchone()

def get_last_unfinished_exam_id(user_id: int) -> Optional[int]:
    """
    获取用户最后一次未完成的考试ID
    
    Args:
        user_id (int): 用户ID
        
    Returns:
        exam_id (Optional[int]): 考试ID，如果不存在则返回None
    """
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT id
        FROM exams
        WHERE user_id = ? AND complete = 0
        ORDER BY restart_at DESC
        LIMIT 1
    ''', (user_id,))
    row = c.fetchone()
    return row['id'] if row else None

def get_exam_data(user_id, exam_id):
    """获取考试数据，用于AJAX页面加载"""
    conn = get_db()
    c = conn.cursor()
    
    # 获取考试记录，包含 restart_at
    c.execute('''
        SELECT 
            id,
            question_ids,
            answers,
            start_at,
            restart_at,
            duration,
            complete,
            score
        FROM exams 
        WHERE id = ? AND user_id = ?
    ''', (exam_id, user_id))
    exam = c.fetchone()
    
    if not exam:
        return None
    
    question_ids = json.loads(exam['question_ids'])
    answers = json.loads(exam['answers']) if exam['answers'] else []
    
    # 如果考试未完成，更新 restart_at 为当前时间（继续考试的时刻）
    if not exam['complete']:
        current_time = datetime.now()
        c.execute('UPDATE exams SET restart_at = ? WHERE id = ?', (current_time, exam_id))
        conn.commit()
    
    # 已用时间即为 duration（之前累加的总时间）
    elapsed_time = exam['duration']
    
    # 获取题目详情
    questions = []
    for idx, qid in enumerate(question_ids):
        q = fetch_question(qid)
        if q:
            # 获取用户已保存的答案（如果有）
            user_answer = answers[idx] if idx < len(answers) else ''
            correct_answer = q.get('answer', '')
            
            # 计算题目是否正确（如果考试已完成）
            is_correct = False
            if exam['complete']:
                user_answer_str = user_answer
                correct_answer_str = "".join(sorted(correct_answer))
                is_correct = user_answer_str == correct_answer_str
            
            questions.append({
                'id': qid,
                'stem': q['stem'],
                'type': q['type'],
                'options': q.get('options', []),
                'answer': user_answer,
                'correct_answer': correct_answer,
                'is_correct': is_correct  # 添加题目是否正确属性
            })
    
    return {
        'exam': exam,
        'questions': questions,
        'elapsed_time': elapsed_time,
        'exam_id': exam_id
    }

def get_last_unfinished_exam(user_id):
    """获取用户最后一次未完成的考试"""
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT id, start_at
        FROM exams
        WHERE user_id = ? AND complete = 0
        ORDER BY start_at DESC
        LIMIT 1
    ''', (user_id,))
    return c.fetchone()

def get_recent_exams(user_id, limit=8):
    """获取用户最近的考试历史（默认8个）"""
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT
            id,
            start_at,
            duration,
            complete,
            score,
            json_array_length(question_ids) as question_count
        FROM exams
        WHERE user_id = ?
        ORDER BY start_at DESC
        LIMIT ?
    ''', (user_id, limit))

    exams = []
    for exam in c.fetchall():
        start_time = datetime.strptime(exam['start_at'], '%Y-%m-%d %H:%M:%S.%f')

        # 格式化持续时间
        hours = exam['duration'] // 3600
        minutes = (exam['duration'] % 3600) // 60
        seconds = exam['duration'] % 60
        formatted_duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        exams.append({
            'id': exam['id'],
            'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'formatted_start_time': start_time.strftime('%m-%d %H:%M'),  # 简化显示
            'duration': exam['duration'],
            'formatted_duration': formatted_duration,
            'completed': bool(exam['complete']),
            'score': exam['score'],
            'question_count': exam['question_count'],
            'status': '已完成' if exam['complete'] else '进行中',
            'score_class': 'text-success' if exam['complete'] and exam['score'] and exam['score'] >= 80 else
                          'text-warning' if exam['complete'] and exam['score'] and exam['score'] >= 60 else
                          'text-danger' if exam['complete'] and exam['score'] and exam['score'] < 60 else
                          'text-muted'
        })

    return exams
