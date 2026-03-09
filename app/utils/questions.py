"""
examcat - 题目辅助函数
"""
import json
import random
from .database import get_db, get_current_bank

def fetch_question(qid):
    """
    Fetch a question by ID from the database.
    
    Args:
        qid (str): The question ID
        
    Returns:
        dict: The question data or None if not found
    """
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM questions WHERE id=?', (qid,))
    row = c.fetchone()
    
    
    if row:
        return {
            'id': row['id'],
            'stem': row['stem'],
            'answer': row['answer'],
            'difficulty': row['difficulty'],
            'type': row['qtype'],
            'category': row['category'],
            'options': json.loads(row['options']) if row['options'] else {},
            'bank_name': row['bank_name']
        }
    return None

def random_question_id(user_id):
    """
    Get a random question ID for a user, excluding questions they've already answered.
    
    Args:
        user_id (int): The user ID
        
    Returns:
        str: A random question ID or None if all questions have been answered
    """
    current_bank = get_current_bank(user_id)
    
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT id FROM questions 
        WHERE bank_name = ?
          AND id NOT IN (
              SELECT question_id FROM history WHERE user_id=?
          )
        ORDER BY RANDOM() 
        LIMIT 1
    ''', (current_bank, user_id))
    row = c.fetchone()
    
    
    if row:
        return row['id']
    return None

def fetch_random_question_ids(num, user_id):
    """
    Fetch multiple random question IDs from the current bank.
    
    Args:
        num (int): The number of question IDs to fetch
        user_id (int): The user ID to get current bank
        
    Returns:
        list: A list of random question IDs
    """
    current_bank = get_current_bank(user_id)
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id FROM questions WHERE bank_name = ? ORDER BY RANDOM() LIMIT ?', 
              (current_bank, num))
    rows = c.fetchall()
    
    return [r['id'] for r in rows]

def is_favorite(user_id, question_id):
    """
    Check if a question is favorited by a user.
    
    Args:
        user_id (int): The user ID
        question_id (str): The question ID
        
    Returns:
        bool: True if favorited, False otherwise
    """
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT 1 FROM favorites WHERE user_id=? AND question_id=?',
              (user_id, question_id))
    is_fav = bool(c.fetchone())
    
    return is_fav