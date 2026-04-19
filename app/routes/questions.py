"""
examcat - 题目路由蓝图
"""
import os
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, make_response, current_app
from ..utils.auth import login_required, get_user_id
from ..utils.questions import fetch_question, get_first_question_id, is_favorite, get_current_sequential_question_id, get_next_sequential_question_id, get_prev_sequential_question_id, get_wrong_question_ids, get_favorite_question_ids
from ..utils.banks import fetch_bank, get_current_bank_id
from ..utils.database import get_db, db_logger, add_history_record, fetch_question_stats, reset_history_record
from ..utils.cookie import set_cookies_from_dict, cookie_logger, update_current_seq_qid_cookie
from ..utils.page_data import get_question_data

questions_bp = Blueprint('questions', __name__, template_folder='../templates/base')

@questions_bp.route('/questions/<int:qid>', methods=['GET', 'POST'])
@login_required
def show(qid):
    """
    查看和回答特定题目
    
    Args:
        qid: 题目ID
        ?mode: 模式 (sequential/wrong/favorite/other)
    """
    # 从查询参数获取mode（优先级：表单 > 查询参数 > 默认值）
    mode = request.form.get('mode') or request.args.get('mode') or 'other'
    user_id = get_user_id()
    question = fetch_question(qid)
    bid = question['bank_id']
    cookies = None
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
              request.headers.get('X-Ajax-Navigation') == 'true'
    is_ajax_nav = request.headers.get('X-Ajax-Navigation') == 'true'

    # 处理POST请求（提交答案）
    if request.method == 'POST':
        if not is_ajax:
            return jsonify({
                'success': False, 
                'message': '非AJAX提交',
                'requires_ajax': True
            }), 400
        
        try:
            # 获取用户答案并判断正误
            user_answer_list = request.form.getlist('answer')
            user_answer_str = "".join(sorted(user_answer_list))
            correct_answer = int(user_answer_str == "".join(sorted(question['answer'])))

            # 提交答案
            add_history_record(user_id, qid, user_answer_str, correct_answer, bid)
            
            # 获取更新后的题目数据
            data = get_question_data(user_id, qid, mode)
            # 添加成功状态
            data['success'] = True
            # 创建JSON响应
            resp = jsonify(data)
            
            # 在顺序模式下，将current_seq_qid更新为下一题的ID
            if mode == 'sequential' and data.get('next_qid'):
                resp = update_current_seq_qid_cookie(resp, qid, data['next_qid'])
                cookie_logger.debug(f"用户{user_id}提交答案后更新current_seq_qid为: {data['next_qid']}")
            
            return resp
            
        except Exception as e:
            db_logger.error(f"提交答案失败: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    # 处理GET请求（查看题目）
    data = get_question_data(user_id, qid, mode)
    if is_ajax_nav:
        html_content = render_template('_partial/_question_content.html', **data)
        
        return jsonify({
            'success': True,
            'html': html_content,
            'styles': [url_for('static', filename='css/question.css')],
            'scripts': [url_for('static', filename='js/question.js')],
            'title': f"题目 {data['question']['order']} | {current_app.config.get('TITLE', 'Examcat')}",
            'page': 'question'
        })
    
    # 普通GET请求，返回完整HTML页面
    resp = make_response(render_template('question.html', **data))
    if cookies:
        resp = set_cookies_from_dict(resp, cookies)
    return resp

@questions_bp.route('/<mode>/start', methods=['GET', 'POST'])
@login_required
def start(mode):
    user_id = get_user_id()
    # 检测是否为AJAX导航请求
    is_ajax_nav = request.headers.get('X-Ajax-Navigation') == 'true'
    
    if mode == 'sequential':
        # 顺序模式：获取当前题库的第一题，并设置cookie
        qid, _ = get_first_question_id(user_id)
    elif mode == 'wrong':
        # 错题模式：获取用户所有错题的第一题（按最后错误时间倒序）
        wrong_ids = get_wrong_question_ids(user_id)
        if not wrong_ids:
            # 如果没有错题，根据请求类型返回不同响应
            if is_ajax_nav:
                return jsonify({'success': False, 'message': '您目前没有错题'})
            else:
                flash('您目前没有错题', 'info')
                return redirect(url_for('banks.banks'))
        qid = wrong_ids[0]
        # 获取题目所属的题库ID
        question = fetch_question(qid)
        if not question:
            if is_ajax_nav:
                return jsonify({'success': False, 'message': '题目不存在'})
            else:
                flash('题目不存在', 'error')
                return redirect(url_for('banks.banks'))
    elif mode == 'favorites':
        # 收藏模式：获取用户所有收藏的第一题（按收藏时间倒序）
        favorite_ids = get_favorite_question_ids(user_id)
        if not favorite_ids:
            if is_ajax_nav:
                return jsonify({'success': False, 'message': '您目前没有收藏题目'})
            else:
                flash('您目前没有收藏题目', 'info')
                return redirect(url_for('banks.banks'))
        qid = favorite_ids[0]
        # 获取题目所属的题库ID
        question = fetch_question(qid)
        if not question:
            if is_ajax_nav:
                return jsonify({'success': False, 'message': '题目不存在'})
            else:
                flash('题目不存在', 'error')
                return redirect(url_for('banks.banks'))
    else:
        # 其他模式：默认使用顺序模式逻辑
        qid, _ = get_first_question_id(user_id)
    
    # 根据请求类型返回不同响应
    if is_ajax_nav:
        # AJAX请求：直接返回题目内容（与show函数格式一致）
        data = get_question_data(user_id, qid, mode)
        html_content = render_template('_partial/_question_content.html', **data)

        return jsonify({
            'success': True,
            'html': html_content,
            'styles': [url_for('static', filename='css/question.css')],
            'scripts': [url_for('static', filename='js/question.js')],
            'title': f"题目 {data['question']['order']} | {current_app.config.get('TITLE', 'Examcat')}",
            'page': 'question'
        })
    else:
        # 普通请求：重定向到题目页面
        resp = make_response(redirect(url_for('questions.show', mode=mode, qid=qid)))
        return resp

@questions_bp.route('/banks/<int:bid>/reset', methods=['GET', 'POST'])
@login_required
def reset(bid):
    """
    重置用户在指定题库的答题记录

    Args:
        bid: 题库ID

    Returns:
        JSON: {'success': true, 'reset_count': N} 或错误信息
        如果是普通GET请求，重定向到首页
    """
    user_id = get_user_id()

    try:
        # 调用数据库重置函数
        reset_count = reset_history_record(user_id, bid)

        # 根据请求类型返回不同的响应
        if request.method == 'POST' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # AJAX请求或POST请求返回JSON
            return jsonify({
                'success': True,
                'reset_count': reset_count
            })
        else:
            # 普通GET请求，重定向到首页
            return redirect(url_for('main.index'))

    except Exception as e:
        db_logger.error(f"重置答题记录失败，用户 {user_id}，题库 {bid}: {e}")
        
        if request.method == 'POST' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500
        else:
            # GET请求出错也重定向到首页
            return redirect(url_for('main.index'))