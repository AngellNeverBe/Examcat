"""
examcat - AJAX
"""
from flask import Blueprint, render_template, jsonify, url_for, request, redirect, current_app
from ..utils.page_data import get_index_data, get_banks_data, get_user_data, get_question_data
from ..utils.cookie import set_cookies_from_dict
from ..utils.auth import get_user_id
from ..utils.database import get_db
from ..utils.banks import get_current_bank_id
from ..utils.exams import get_last_unfinished_exam, get_recent_exams, get_exam_data

ajax_bp = Blueprint('ajax', __name__, template_folder='../templates/_partial')

@ajax_bp.route('/ajax/<page_name>', methods=['GET'])
def ajax_page(page_name):
    """统一处理 AJAX 页面请求，返回 JSON 格式的片段和资源"""

    app_title = current_app.config.get('TITLE', 'Examcat')  # 默认值 Examcat
    cookies = None
    
    # 如果不是 AJAX 请求，可以重定向到完整页面
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
              request.headers.get('X-Ajax-Navigation') == 'true'
    
    if not is_ajax:
        # 非 AJAX 请求，重定向到对应的完整页面
        if page_name == 'login':
            return redirect(url_for('auth.login'))
        elif page_name == 'register':
            return redirect(url_for('auth.register'))
        elif page_name == 'index':
            return redirect(url_for('main.index'))
        elif page_name == 'banks':
            return redirect(url_for('banks.banks'))
        elif page_name == 'user':
            return redirect(url_for('auth.user_index'))
        elif page_name == 'exams':
            return redirect(url_for('exams.exams_index'))
        elif page_name.startswith('question_'):
            return redirect(url_for('questions.show'))
        elif page_name.startswith('exam-'):
            # 解析考试ID并重定向到完整考试页面
            parts = page_name.split('-')
            if len(parts) == 2 and parts[0] == 'exam':
                try:
                    exam_id = int(parts[1])
                except ValueError:
                    return jsonify({'error': '无效的考试ID'}), 400
                return redirect(url_for('exams.exam_main', exam_id=exam_id))
        # ... 其他页面
        else:
            return jsonify({'error': '页面不存在'}), 404

    # 根据页面名称返回对应的数据
    if page_name == 'login':
        html_content = render_template('_login_form.html')
        styles = [url_for('static', filename='css/login.css')]
        scripts = [url_for('static', filename='js/login.js')]
        title = f'登录 | {app_title}'

    elif page_name == 'register':
        html_content = render_template('_register_form.html')
        styles = [url_for('static', filename='css/register.css')]
        scripts = [url_for('static', filename='js/register.js')]
        title = f'注册 | {app_title}'

    elif page_name == 'index':
        user_id = get_user_id()
        if not user_id:
            return jsonify({'success': False, 'error': '请先登录'}), 401        
        data, cookies = get_index_data(user_id)
        html_content = render_template('_index_content.html', **data)
        styles = [url_for('static', filename='css/index.css')]
        scripts = [url_for('static', filename='js/index.js')]
        title = f'首页 | {app_title}'

    elif page_name == 'banks':
        user_id = get_user_id()
        if not user_id:
            return jsonify({'success': False, 'error': '请先登录'}), 401
        
        # 获取分类参数
        category = request.args.get('category')
        data = get_banks_data(user_id, category=category)
        html_content = render_template('_banks_content.html', **data)
        styles = [url_for('static', filename='css/banks.css')]
        scripts = [url_for('static', filename='js/banks.js')]
        title = f'题库 | {app_title}'

    elif page_name == 'user':
        user_id = get_user_id()
        if not user_id:
            return jsonify({'success': False, 'error': '请先登录'}), 401
        
        # 使用统一的用户数据获取函数
        data = get_user_data(user_id)
        
        # 渲染用户页面模板，传递所有数据
        html_content = render_template('_profile_content.html', **data)
        styles = [url_for('static', filename='css/user.css')]
        scripts = [url_for('static', filename='js/user.js')]
        title = f'个人 | {app_title}'

    elif page_name == 'exams':
        user_id = get_user_id()
        if not user_id:
            return jsonify({'success': False, 'error': '请先登录'}), 401
        
        # 获取考试数据
        last_unfinished = get_last_unfinished_exam(user_id)
        recent_exams = get_recent_exams(user_id, limit=8)
        
        # 渲染考试页面模板
        html_content = render_template('_exams_content.html',
                                      last_unfinished_exam=last_unfinished,
                                      recent_exams=recent_exams)
        styles = [url_for('static', filename='css/exams.css')]
        scripts = [url_for('static', filename='js/exams.js')]
        title = f'考试 | {app_title}'

    elif page_name.startswith('question-'):
        # 从查询参数获取mode
        mode = request.args.get('mode', 'sequential')
        # 从page_name解析参数，例如: question-100
        # 解析格式: question-{qid}
        parts = page_name.split('-')
        if len(parts) == 2 and parts[0] == 'question':
            qid = int(parts[1])
            
            # 验证用户权限
            user_id = get_user_id()
            if not user_id:
                return jsonify({'success': False, 'error': '请先登录'}), 401
            
            # 获取题目数据
            data = get_question_data(user_id, qid, mode)
            data['mode'] = mode  # 确保包含mode
            
            return jsonify({
                'success': True,
                'html': render_template('_partial/_question_content.html', **data),
                'styles': [url_for('static', filename='css/question.css')],
                'scripts': [url_for('static', filename='js/question.js')],
                'title': f"题目 {data['question']['order']} | {app_title}"
            })

    elif page_name.startswith('exam-'):
        # 从page_name解析参数，例如: exam-123
        parts = page_name.split('-')
        if len(parts) == 2 and parts[0] == 'exam':
            try:
                exam_id = int(parts[1])
            except ValueError:
                return jsonify({'error': '无效的考试ID'}), 400
            
            # 验证用户权限
            user_id = get_user_id()
            if not user_id:
                return jsonify({'success': False, 'error': '请先登录'}), 401
            
            data = get_exam_data(user_id, exam_id)
            
            if not data:
                return jsonify({'success': False, 'error': '考试不存在或无权访问'}), 404
            
            return jsonify({
                'success': True,
                'html': render_template('_partial/_exam_content.html', **data),
                'styles': [url_for('static', filename='css/exam.css')],
                'scripts': [url_for('static', filename='js/exam.js')],
                'title': f"模拟考试 | {app_title}",
                'page': 'exam'
            })

    else:
        return jsonify({'error': '页面不存在'}), 404
    
    resp = jsonify({
            'success': True,
            'html': html_content,
            'styles': styles,
            'scripts': scripts,
            'title': title,
            'page': page_name
        })
    if cookies:
        resp = set_cookies_from_dict(resp, cookies)
        
    return resp