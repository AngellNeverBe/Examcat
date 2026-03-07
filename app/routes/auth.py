"""
examcat - 认证路由蓝图
"""
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from ..utils.database import get_db, get_first_bank, load_questions_to_db
from ..utils.auth import login_required, is_logged_in, get_user_id, admin_required, verify_admin_credentials, is_admin, ADMIN_CREDENTIALS

auth_bp = Blueprint('auth', __name__, template_folder='../templates/base_auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Route for user registration."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # 检查是否尝试注册管理员账号
        if username == 'admin':
            flash("不能注册管理员账号", "error")
            return render_template('register.html')
            
        # Input validation
        if not username or not password:
            flash("用户名和密码不能为空", "error")
            return render_template('register.html')
            
        if password != confirm_password:
            flash("两次输入的密码不一致", "error")
            return render_template('register.html')
            
        if len(password) < 6:
            flash("密码长度不能少于6个字符", "error")
            return render_template('register.html')
        
        conn = get_db()
        c = conn.cursor()
        
        # Check if username exists
        c.execute('SELECT id FROM users WHERE username=?', (username,))
        if c.fetchone():
            conn.close()
            flash("用户名已存在，请更换用户名", "error")
            return render_template('register.html')
        
        # Get first available bank
        first_bank = get_first_bank()
        if not first_bank:
            first_bank = 'questions.csv'
        
        # Create new user
        password_hash = generate_password_hash(password)
        c.execute('INSERT INTO users (username, password_hash, current_bank) VALUES (?,?,?)', 
                  (username, password_hash, first_bank))
        conn.commit()
        conn.close()
        flash("注册成功，请登录", "success")
        return redirect(url_for('auth.login'))
        
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Route for user login (普通用户和管理员共用)."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash("用户名和密码不能为空", "error")
            return render_template('login.html')
        
        # 首先尝试管理员登录
        if verify_admin_credentials(username, password):

            conn = get_db()
            c = conn.cursor()
            # Check if username exists
            c.execute('SELECT id FROM users WHERE username=?', (username,))
            user = c.fetchone()
            if not user:
                # Get first available bank
                first_bank = get_first_bank()
                if not first_bank:
                    first_bank = 'questions.csv'
                c.execute('INSERT INTO users (username, password_hash, current_bank) VALUES (?,?,?)', 
                        (username, ADMIN_CREDENTIALS[username], first_bank))
                conn.commit()
                flash("管理员第一次登录，信息已记录，请重新登录", "success")
                conn.close()
                return redirect(url_for('auth.login'))
            
            print(user['id'])
            session['user_id'] = user['id']
            session['is_admin'] = True            

            # Ensure the user has a current_bank set
            c.execute('SELECT current_bank FROM users WHERE id = ?', (user['id'],))
            current_bank_row = c.fetchone()
            
            if not current_bank_row or not current_bank_row['current_bank']:
                # Set first available bank for existing users
                first_bank = get_first_bank()
                if first_bank:
                    c.execute('UPDATE users SET current_bank = ? WHERE id = ?', 
                             (first_bank, user['id']))
                else:
                    c.execute('UPDATE users SET current_bank = ? WHERE id = ?', 
                             ('questions.csv', user['id']))
                conn.commit()
                current_bank = first_bank if first_bank else 'questions.csv'
            else:
                current_bank = current_bank_row['current_bank']
            
            # Check if questions exist for this bank, if not load them
            c.execute('SELECT COUNT(*) as cnt FROM questions WHERE bank_name = ?', (current_bank,))
            if c.fetchone()['cnt'] == 0:
                load_questions_to_db(conn, current_bank)
            
            conn.close()

            flash("管理员登录成功", "success")
            # Redirect to 'next' parameter if provided
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('main.index'))
        
        # 如果不是管理员，尝试普通用户登录
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT id, password_hash FROM users WHERE username=?', (username,))
        user = c.fetchone()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['is_admin'] = False  # 明确设置为普通用户
            
            # Ensure the user has a current_bank set
            c.execute('SELECT current_bank FROM users WHERE id = ?', (user['id'],))
            current_bank_row = c.fetchone()
            
            if not current_bank_row or not current_bank_row['current_bank']:
                # Set first available bank for existing users
                first_bank = get_first_bank()
                if first_bank:
                    c.execute('UPDATE users SET current_bank = ? WHERE id = ?', 
                             (first_bank, user['id']))
                else:
                    c.execute('UPDATE users SET current_bank = ? WHERE id = ?', 
                             ('questions.csv', user['id']))
                conn.commit()
                current_bank = first_bank if first_bank else 'questions.csv'
            else:
                current_bank = current_bank_row['current_bank']
            
            # Check if questions exist for this bank, if not load them
            c.execute('SELECT COUNT(*) as cnt FROM questions WHERE bank_name = ?', (current_bank,))
            if c.fetchone()['cnt'] == 0:
                load_questions_to_db(conn, current_bank)
            
            conn.close()
            
            flash("登录成功", "success")
            
            # Redirect to 'next' parameter if provided
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
                
            return redirect(url_for('main.index'))
        else:
            flash("登录失败，用户名或密码错误", "error")
            
        conn.close()
            
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    """Route for user logout."""
    user_type = "管理员" if is_admin() else "用户"
    session.clear()
    flash(f"{user_type}已成功退出登录", "success")
    return redirect(url_for('auth.login'))