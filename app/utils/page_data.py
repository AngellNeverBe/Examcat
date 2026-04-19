"""
examcat - 页面信息提供模块
"""
import json
from ..utils.auth import get_user_id, _is_admin
from ..utils.database import get_db, fetch_question_stats
from ..utils.banks import fetch_bank, get_current_bank_id, fetch_all_banks
from ..utils.questions import fetch_question, get_current_sequential_question_id, is_favorite, get_next_sequential_question_id, get_prev_sequential_question_id, get_question_completion, fetch_qids_by_bid, get_wrong_question_ids, get_favorite_question_ids
from ..utils.auth import get_user_overall_stats, get_user_type_stats, get_user_category_stats, get_user_worst_questions, get_user_all_favorites, get_user_all_wrong_questions, fetch_user_question_stats, fetch_user_question_stats_by_category, fetch_user_qids_by_bid

def get_index_data(user_id):
    """返回首页数据"""
    current_bank_id, cookies_bank_id = get_current_bank_id(user_id)
    bank_data = fetch_bank(current_bank_id)
    question_stats = fetch_user_question_stats(user_id, current_bank_id)
    current_seq_qid, cookies_current_seq_qid = get_current_sequential_question_id(user_id)
    question_data = fetch_question(current_seq_qid)

    # 获取题目ID到order的映射关系
    question_id_mapping = fetch_qids_by_bid(current_bank_id)

    # 获取用户在该题库下的正确和错误题目ID列表
    user_question_status = fetch_user_qids_by_bid(user_id, current_bank_id)

    data = {
        'bank': bank_data,
        'question': question_data,
        'current_bid': current_bank_id,
        'current_seq_qid': current_seq_qid,
        'question_stats': question_stats,
        'question_id_mapping': question_id_mapping,  # {question_id: order}
        'user_question_status': user_question_status  # {'correct': [id列表], 'wrong': [id列表]}
    }
    cookies = {**cookies_bank_id, **cookies_current_seq_qid}

    return data, cookies

def get_banks_data(user_id, category=None):
    """返回题库页数据
    
    Args:
        user_id (int): 用户ID
        category (str, optional): 分类过滤参数
        
    Returns:
        dict: 包含以下数据的字典：
            - categories: 分类列表
            - banks_by_category: 按分类组织的题库字典
            - current_bank_id: 当前题库ID
            - category_stats: 每个分类的统计信息
            - is_admin: 是否是管理员
            - banks: 题库列表（过滤后）
            - active_category: 激活的分类标签
    """
    current_bank_id, _ = get_current_bank_id(user_id)

    # 获取所有题库及其统计信息（使用新的辅助函数）
    raw_banks = fetch_all_banks(user_id)
    all_categories = ['大一', '大二', '大三', '大四', '大五', '其他']

    # 处理题库数据
    banks = []
    for bank in raw_banks:
        category_count = bank['category_count']
        total = bank['total']
        answered = bank['answered']
        correct = bank['correct']
        wrong = bank['wrong']
        unanswered = total - answered

        # 计算百分比（基于total）
        correct_percentage = round((correct / total * 100), 2) if total > 0 else 0
        wrong_percentage = round((wrong / total * 100), 2) if total > 0 else 0
        unanswered_percentage = round((unanswered / total * 100), 2) if total > 0 else 0

        # 为每个分类计算统计数据（使用实际统计数据，不再按比例分配）
        category_count_stats = {}
        if category_count and total > 0:
            for cat_name, cat_count in category_count.items():
                # 获取该分类的实际答题统计
                cat_stats = fetch_user_question_stats_by_category(user_id, bank['id'], cat_name)

                category_count_stats[cat_name] = {
                    'count': cat_count,
                    'correct': cat_stats['correct'],
                    'wrong': cat_stats['wrong'],
                    'answered': cat_stats['answered'],
                    'unanswered': cat_stats['unanswered'],
                    'correct_percentage': cat_stats['correct_total_percentage'],
                    'wrong_percentage': cat_stats['wrong_total_percentage'],
                    'unanswered_percentage': cat_stats['unanswered_percentage']
                }

        # 将题库数据添加到banks列表
        banks.append({
            'id': bank['id'],
            'name': bank['name'],
            'type': bank['type'],
            'category': bank['category'],
            'total': total,
            'answered': answered,
            'correct': correct,
            'wrong': wrong,
            'unanswered': unanswered,
            'progress_percentage': round((answered / total * 100), 1) if total > 0 else 0,
            'correct_percentage': correct_percentage,
            'wrong_percentage': wrong_percentage,
            'unanswered_percentage': unanswered_percentage,
            'is_current': bank['id'] == current_bank_id,
            'needs_loading': False,
            'category_count': category_count,
            'category_count_stats': category_count_stats
        })

    # 计算分类统计（基于所有题库）
    category_stats = {}
    for cat in all_categories:
        cat_banks = [b for b in banks if b['category'] == cat]
        total_banks = len(cat_banks)
        total_questions = sum(b['total'] for b in cat_banks)
        total_answered = sum(b['answered'] for b in cat_banks)
        total_correct = sum(b['correct'] for b in cat_banks)
        total_wrong = sum(b['wrong'] for b in cat_banks)

        # 计算分类级别的百分比
        correct_percentage = round((total_correct / total_questions * 100), 2) if total_questions > 0 else 0
        wrong_percentage = round((total_wrong / total_questions * 100), 2) if total_questions > 0 else 0
        unanswered_percentage = round(((total_questions - total_answered) / total_questions * 100), 2) if total_questions > 0 else 0

        category_stats[cat] = {
            'bank_count': total_banks,
            'total_questions': total_questions,
            'answered_questions': total_answered,
            'correct_questions': total_correct,
            'wrong_questions': total_wrong,
            'progress_percentage': round((total_answered / total_questions * 100), 1) if total_questions > 0 else 0,
            'correct_percentage': correct_percentage,
            'wrong_percentage': wrong_percentage,
            'unanswered_percentage': unanswered_percentage
        }

    # 确定激活的分类
    active_category = '其他'  # 默认

    # 验证category参数
    if category and category in all_categories:
        active_category = category
    else:
        # 根据当前题库确定
        for bank in banks:
            if bank['id'] == current_bank_id:
                active_category = bank['category']
                break

    # 过滤题库（如果指定了分类）
    filtered_banks = banks
    if category and category in all_categories:
        filtered_banks = [bank for bank in banks if bank['category'] == category]

    # 按分类分组（过滤后的题库）
    banks_by_category = {cat: [] for cat in all_categories}
    for bank in filtered_banks:
        banks_by_category[bank['category']].append(bank)

    # 检查用户是否是管理员
    try:
        is_admin = _is_admin()
    except RuntimeError:
        # 在没有请求上下文的情况下（如测试环境），默认为非管理员
        is_admin = False

    return {
        'categories': all_categories,
        'banks_by_category': banks_by_category,
        'current_bank_id': current_bank_id,
        'category_stats': category_stats,
        'is_admin': is_admin,
        'banks': filtered_banks,  # 过滤后的题库列表
        'active_category': active_category
    }

def get_user_data(user_id):
    """返回用户中心页面所需的所有数据（基于所有题库）
    
    Args:
        user_id (int): 用户ID
        
    Returns:
        dict: 包含以下数据的字典：
            - user_data: 用户基本信息（id, username, email, created_at）
            - total: 所有题库已答题总数
            - correct_count: 所有题库答对题数
            - wrong_count: 所有题库答错题数
            - overall_accuracy: 所有题库总体正确率
            - type_stats: 按题型统计的列表（所有题库）
            - category_stats: 按分类统计的列表（所有题库）
            - worst_questions: 最多错误的题目列表（所有题库，最多10条）
            - exam_history: 考试历史列表（最多10条）
            - favorites: 收藏题目列表（所有题库）
            - wrong_questions: 错题列表（所有题库）
            - wrong_total_count: 错题总错误次数（所有题库）
            - wrong_unique_categories_count: 错题涉及分类数量（所有题库）
            - wrong_once_count: 只错一次的题目数量（所有题库）
    """
    conn = get_db()
    c = conn.cursor()
    
    # 获取用户基本信息
    c.execute('SELECT id, username, email, created_at FROM users WHERE id = ?', (user_id,))
    user_data = c.fetchone()
    
    # 获取用户在所有题库下的总体统计
    overall_stats = get_user_overall_stats(user_id)
    total = overall_stats['total']
    correct = overall_stats['correct']
    wrong = overall_stats['wrong']
    correct_count = overall_stats['correct_count']
    wrong_count = overall_stats['wrong_count']
    overall_accuracy = overall_stats['overall_accuracy']
    
    # 获取题型统计（所有题库）
    type_stats = get_user_type_stats(user_id)
    
    # 获取分类统计（所有题库）
    category_stats = get_user_category_stats(user_id)
    
    # 获取最多错误的题目（所有题库）
    # worst_questions = get_user_worst_questions(user_id, limit=10)
    
    # 获取收藏数据（所有题库）
    favorites_data = get_user_all_favorites(user_id)
    
    # 获取错题数据（所有题库）
    wrong_stats = get_user_all_wrong_questions(user_id)
    wrong_questions_data = wrong_stats['wrong_questions']
    wrong_total_count = wrong_stats['wrong_total_count']
    wrong_unique_categories_count = wrong_stats['wrong_unique_categories_count']
    wrong_once_count = wrong_stats['wrong_once_count']
    
    return {
        'user_data': user_data,
        'total': total,
        'correct':correct,
        'wrong':wrong,
        'correct_count': correct_count,
        'wrong_count': wrong_count,
        'overall_accuracy': overall_accuracy,
        'type_stats': type_stats,
        'category_stats': category_stats,
        # 'worst_questions': worst_questions,
        'favorites': favorites_data,
        'wrong_questions': wrong_questions_data,
        'wrong_total_count': wrong_total_count,
        'wrong_unique_categories_count': wrong_unique_categories_count,
        'wrong_once_count': wrong_once_count
    }

def get_question_data(user_id, qid, mode=None):
    """返回题目页数据"""
    q = fetch_question(qid)
    bid = q['bank_id']
    b = fetch_bank(bid)
    is_fav = is_favorite(user_id, qid)
    stats = fetch_question_stats(qid)
    # 根据模式计算下一题和上一题ID
    next_qid = None
    prev_qid = None

    if mode == 'sequential':
        # 顺序模式：按题库内的order顺序
        next_qid = get_next_sequential_question_id(qid)
        prev_qid = get_prev_sequential_question_id(qid)
    elif mode == 'wrong':
        # 错题模式：在所有错题列表中导航
        wrong_ids = get_wrong_question_ids(user_id)
        if qid in wrong_ids:
            idx = wrong_ids.index(qid)
            if idx > 0:
                prev_qid = wrong_ids[idx - 1]
            if idx < len(wrong_ids) - 1:
                next_qid = wrong_ids[idx + 1]
    elif mode == 'favorites':
        # 收藏模式：在所有收藏题目列表中导航
        favorite_ids = get_favorite_question_ids(user_id)
        if qid in favorite_ids:
            idx = favorite_ids.index(qid)
            if idx > 0:
                prev_qid = favorite_ids[idx - 1]
            if idx < len(favorite_ids) - 1:
                next_qid = favorite_ids[idx + 1]
    else:
        # 其他模式：默认按顺序模式处理
        next_qid = get_next_sequential_question_id(qid)
        prev_qid = get_prev_sequential_question_id(qid)

    # 获取完成状态
    completion = get_question_completion(user_id, qid)

    # 根据完成状态构造结果消息
    result_msg = None
    if completion['completed']:
        if completion['correct']:
            result_msg = "回答正确"
        else:
            result_msg = f"回答错误，正确答案：{q['answer']}"

    return {
        'question': q,
        'bank':b,
        'bid': bid,
        'next_qid': next_qid,
        'prev_qid': prev_qid,
        'is_favorite': is_fav,
        'stats': stats,
        'mode': mode,
        'completed': completion['completed'],
        'last_answer': completion['last_answer'],
        'user_answer': completion['user_answer'],
        'correct': completion['correct'],
        'result_msg': result_msg
    }