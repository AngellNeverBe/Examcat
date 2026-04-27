"""
examcat - 认证&用户路由蓝图
"""
import os
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from ..utils.database import get_db, db_logger
from ..utils.auth import validate_username, validate_username_update, validate_email, validate_passward, verify_admin_credentials, ADMIN_CREDENTIALS, login_required
from ..utils.banks import get_current_bank_id
from ..utils.page_data import get_user_data
from ..utils.database import get_db, db_logger

auth_bp = Blueprint('auth', __name__, template_folder='../templates/base_auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Route for user registration."""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        verify_username = validate_username(username)
        verify_email = validate_email(email)
        verify_passward = validate_passward(password, confirm_password)

        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if not verify_username[0]:
            if is_ajax:
                return jsonify({'success': verify_username[0], 'message': verify_username[1]})
            flash(verify_username[1], "error")
            return render_template('register.html')

        if not verify_email[0]:
            if is_ajax:
                return jsonify({'success': verify_email[0], 'message': verify_email[1]})
            flash(verify_email[1], "error")
            return render_template('register.html')
        
        if not verify_passward[0]:
            if is_ajax:
                return jsonify({'success': verify_passward[0], 'message': verify_passward[1]})
            flash(verify_passward[1], "error")
            return render_template('register.html')
        
        conn = get_db()
        c = conn.cursor()
        password_hash = generate_password_hash(password)
        c.execute('INSERT INTO users (username, email, password_hash) VALUES (?,?,?)', 
                  (username, email, password_hash))
        conn.commit()
        db_logger.info(f"[{os.getpid()}] register: 用户{username}")
        
        if is_ajax:
            # AJAX请求：返回JSON响应
            return jsonify({
                'success': True,
                'message': '注册成功，请登录',
                'redirect_url': url_for('ajax.ajax_page', page_name='login')
            })
        else:
            # 传统请求：保持原有行为
            flash("注册成功，请登录", "success")
            return redirect(url_for('auth.login'))
        
    # GET请求：渲染注册页面
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Route for user login (普通用户和管理员共用)."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if not username or not password:
            if is_ajax:
                return jsonify({'success': False, 'message': '用户名和密码不能为空'})
            flash("用户名和密码不能为空", "error")
            return render_template('login.html')
        
        # ============= 管理员登录 ==============
        if verify_admin_credentials(username, password):

            conn = get_db()
            c = conn.cursor()
            # Check if username exists
            c.execute('SELECT id, email FROM users WHERE username=?', (username,))
            user = c.fetchone()
            if not user:
                c.execute('INSERT INTO users (username, email, password_hash) VALUES (?,?,?)', 
                        (username, '', ADMIN_CREDENTIALS[username]))
                conn.commit()
                flash("管理员第一次登录，信息已记录，请重新登录", "success")
                
                return redirect(url_for('auth.login'))
            
            session['user_id'] = user['id']
            session['username'] = username
            session['email'] = user['email'] if user['email'] else '未设置'
            session['is_admin'] = True

            if is_ajax:
                return jsonify({
                    'success': True,
                    'message': f'欢迎，{username} !',
                    'redirect_url': url_for('main.index')
                })
            else:
                flash(f"欢迎，{username} !", "success")
                return redirect(url_for('main.index'))
        
        # ============= 普通用户登录 ==============
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT id, email, password_hash FROM users WHERE username=?', (username,))
        user = c.fetchone()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = username
            session['email'] = user['email'] if user['email'] else '未设置'
            session['is_admin'] = False
                        
            if is_ajax:
                return jsonify({
                    'success': True,
                    'message': f'欢迎，{username}！',
                    'redirect_url': url_for('main.index')
                })
            else:
                flash(f"欢迎，{username}！", "success")
                return redirect(url_for('main.index'))
        else:
            # 登录失败的处理
            if is_ajax:
                return jsonify({'success': False, 'message': '登录失败，用户名或密码错误'})
            else:
                flash("登录失败，用户名或密码错误", "error")
                
    # GET请求：渲染登录页面
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    """Route for user logout."""
    session.clear()
    flash("您已成功退出登录", "success")
    return redirect(url_for('auth.login'))


@auth_bp.route('/user')
@login_required
def user_index():
    """用户个人资料页面"""
    user_id = session['user_id']
    
    # 使用统一的用户数据获取函数
    data = get_user_data(user_id)
    
    # 渲染用户页面模板，传递所有数据
    return render_template('base/user.html', **data)

@auth_bp.route('/user/update', methods=['POST'])
@login_required
def update_profile():
    """更新用户个人资料（用户名/邮箱）"""
    user_id = session['user_id']
    username = request.form.get('username')
    email = request.form.get('email')

    # 至少需要一个字段
    if not username and not email:
        return jsonify({'success': False, 'message': '请提供要修改的用户名或邮箱'})

    # 验证用户名（如果提供了）
    if username:
        # 管理员不允许修改用户名
        if session.get('is_admin'):
            return jsonify({'success': False, 'message': '管理员不允许修改用户名'})

        if username == session.get('username'):
            # 与当前用户名相同，无需修改
            pass
        else:
            valid, msg = validate_username_update(username, user_id)
            if not valid:
                return jsonify({'success': False, 'message': msg})

    # 验证邮箱（如果提供了）
    if email:
        valid, msg = validate_email(email)
        if not valid:
            return jsonify({'success': False, 'message': msg})

    # 执行数据库更新
    conn = get_db()
    c = conn.cursor()

    updated_fields = []

    if username and username != session.get('username'):
        c.execute('UPDATE users SET username = ? WHERE id = ?', (username, user_id))
        session['username'] = username
        updated_fields.append('用户名')
        db_logger.info(f"[{os.getpid()}] update_profile: 用户{user_id} 改名 -> {username}")

    if email:
        c.execute('UPDATE users SET email = ? WHERE id = ?', (email, user_id))
        session['email'] = email
        updated_fields.append('邮箱')

    conn.commit()

    if not updated_fields:
        return jsonify({'success': True, 'message': '资料无需更新'})

    return jsonify({
        'success': True,
        'message': f"{'、'.join(updated_fields)}已更新"
    })