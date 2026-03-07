"""
examcat - 认证辅助函数
"""
from functools import wraps
from flask import session, request, redirect, url_for, flash
from werkzeug.security import check_password_hash, generate_password_hash

# 管理员账号配置（密码使用 generate_password_hash 生成）
ADMIN_CREDENTIALS = {
    'admin':'pbkdf2:sha256:600000$JFYTJtNYkvSIlL2z$37f83bc130fb93a5523cee128e934c0bdfb86cffb53eec4e8500b7e3aee8e0a4'
}

def login_required(f):
    """装饰器：要求登录"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """装饰器：要求管理员权限"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin():
            flash("需要管理员权限才能访问此页面", "error")
            if is_logged_in():
                return redirect(url_for('main.index'))
            else:
                return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def is_logged_in():
    """检查用户是否登录"""
    return 'user_id' in session

def is_admin():
    """检查当前用户是否为管理员"""
    return session.get('is_admin', False)

def get_user_id():
    """获取当前用户ID"""
    return session.get('user_id')

def verify_admin_credentials(username, password):
    """验证管理员账号密码"""
    if username in ADMIN_CREDENTIALS:
        admin_passwd_hash = ADMIN_CREDENTIALS[username]
        if check_password_hash(admin_passwd_hash, password):
            return True
    return None