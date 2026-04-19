"""
examcat - 主页面路由蓝图
"""
from flask import Blueprint, render_template, redirect, url_for, flash, make_response, jsonify
from ..utils.auth import login_required, get_user_id
from ..utils.database import reset_history_record
from ..utils.banks import fetch_bank
from ..utils.page_data import get_index_data
from ..utils.cookie import set_cookies_from_dict

main_bp = Blueprint('main', __name__, template_folder='../templates/base')

@main_bp.route('/')
@login_required
def index():
    """Route to index."""
    user_id = get_user_id()

    # 获取首页所需数据和cookies
    data, cookies = get_index_data(user_id)
    resp = make_response(render_template('index.html', **data))
    if cookies:
        resp = set_cookies_from_dict(resp, cookies)
    return resp

@main_bp.route('/banks/<int:bid>/history/reset', methods=['POST'])
@login_required
def reset_history(bid: int):
    """
    重置用户在指定题库的答题记录
    
    Args:
        bid (int): 题库ID
        
    Returns:
        JSON响应
    """
    try:
        user_id = get_user_id()
        
        # 验证题库是否存在
        bank_data = fetch_bank(bid)
        if not bank_data:
            return jsonify({'success': False, 'message': '题库不存在'}), 404
        
        # 重置答题记录
        reset_count = reset_history_record(user_id, bid)
        
        # 清除相关的cookie缓存
        response = make_response(jsonify({
            'success': True, 
            'message': f'已重置答题记录，共重置{reset_count}条记录',
            'reset_count': reset_count
        }))
        
        # 清除当前题目相关的cookie，因为重置后应该从第一题开始
        response.delete_cookie('current_seq_qid')
        
        return response
        
    except Exception as e:
        # logger.error(f"重置答题记录失败，用户ID {get_user_id()}，题库ID {bid}: {e}")
        return jsonify({'success': False, 'message': f'重置失败: {str(e)}'}), 500