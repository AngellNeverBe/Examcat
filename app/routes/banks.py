"""
examcat - 题库管理路由蓝图
"""
import os
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from ..utils.auth import login_required, get_user_id, admin_required
from ..utils.database import get_db, db_logger
from ..utils.banks import get_current_bank_id, load_bank, add_bank, switch_current_bank
from ..utils.page_data import get_banks_data

banks_bp = Blueprint('banks', __name__, template_folder='../templates/base')

@banks_bp.route('/banks')
@login_required
def banks():
    """Route to banks."""
    user_id = get_user_id()    
    data = get_banks_data(user_id)
    return render_template('banks.html', **data)

@banks_bp.route('/load_bank', methods=['POST'])
@admin_required
def load_all_banks():
    """手动加载题库路由"""
    result = load_bank()
    
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if is_ajax:
        # AJAX 请求返回 JSON
        if not result['errors'] and not result['missing_csv']:
            status = 'success'
            message = f"成功加载 {result['added']} 个新题库"
        elif result['errors'] or result['missing_csv']:
            status = 'partial' if result['added'] > 0 else 'error'
            message = f"加载完成：新增 {result['added']} 个，失败 {len(result['errors'])} 个，缺失文件 {len(result['missing_csv'])} 个"
        else:
            status = 'info'
            message = "没有发现新题库"
        
        return jsonify({
            'status': status, 
            'message': message, 
            'redirect_url': url_for('banks.banks')
        })
    else:
        if result['added'] > 0:
            flash(f"成功加载 {result['added']} 个新题库", "success")
        if result['errors']:
            for err in result['errors']:
                flash(err, "danger")
        if result['missing_csv']:
            for miss in result['missing_csv']:
                flash(miss, "warning")
        if result['added'] == 0 and not result['errors'] and not result['missing_csv']:
            flash("没有发现新题库", "info")
        
        return redirect(url_for('banks.banks'))

@banks_bp.route('/upload_bank', methods=['POST'])
@admin_required
def upload_bank():
    """Route to upload a new question bank CSV file."""
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if 'bank_file' not in request.files:
        if is_ajax:
            return jsonify({'success': False, 'message': '没有选择文件'})
        flash("没有选择文件", "error")
        return redirect(url_for('banks.banks'))
    
    file = request.files['bank_file']
    if file.filename == '':
        if is_ajax:
            return jsonify({'success': False, 'message': '没有选择文件'})
        flash("没有选择文件", "error")
        return redirect(url_for('banks.banks'))
    
    if not file.filename.endswith('.csv'):
        if is_ajax:
            return jsonify({'success': False, 'message': '只支持CSV格式文件'})
        flash("只支持CSV格式文件", "error")
        return redirect(url_for('banks.banks'))
    
    try:
        # 保存上传文件
        banks_dir = './questions-bank'
        os.makedirs(banks_dir, exist_ok=True)
        filepath = os.path.join(banks_dir, file.filename)
        file.save(filepath)
        
        # 提取题库名（去除.csv后缀）
        bankname = os.path.splitext(file.filename)[0]
        
        # 调用add_bank导入题库
        bank_id = add_bank(filepath, bankname=bankname)
        
        if is_ajax:
            return jsonify({
                'success': True,
                'message': f'题库 {bankname} 上传成功, 新题库id为 {bank_id}',
                'redirect_url': url_for('banks.banks')
            })
        flash(f"题库 {bankname} 上传成功", "success")
    except Exception as e:
        db_logger.error(f"上传题库失败: {str(e)}")
        if is_ajax:
            return jsonify({
                'success': False, 
                'message': f'上传题库时出错: {str(e)}', 
                'redirect_url': url_for('banks.banks')
            })
        flash(f"上传题库时出错: {str(e)}", "error")
    
    return redirect(url_for('banks.banks'))

@banks_bp.route('/delete_bank', methods=['POST'])
@admin_required
def delete_bank():
    """Route to delete a question bank."""
    bank_name = request.form.get('bank_name')
    user_id = get_user_id()
    current_bank = get_current_bank_id(user_id)
    
    if not bank_name:
        flash("请选择要删除的题库", "error")
        return redirect(url_for('banks.banks'))
    
    # Don't allow deleting the current bank
    if bank_name == current_bank:
        # Find another bank to switch to
        available_banks = get_available_banks()
        other_banks = [b for b in available_banks if b != bank_name]
        
        if other_banks:
            # Switch to another bank first
            new_bank = other_banks[0]
            set_current_bank(user_id, new_bank)
        else:
            flash("不能删除唯一的题库", "error")
            return redirect(url_for('banks.banks'))
    
    try:
        # Delete from database first
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM questions WHERE bank_name = ?', (bank_name,))
        
        # Also delete related history and favorites
        c.execute('''
            DELETE FROM history 
            WHERE question_id IN (
                SELECT id FROM questions WHERE bank_name = ?
            )
        ''', (bank_name,))
        
        c.execute('''
            DELETE FROM favorites 
            WHERE question_id IN (
                SELECT id FROM questions WHERE bank_name = ?
            )
        ''', (bank_name,))
        
        conn.commit()
        
        
        # Delete the file
        # 确保bank_name有.csv后缀来查找文件
        if not bank_name.endswith('.csv'):
            file_name = bank_name + '.csv'
        else:
            file_name = bank_name
            bank_name = bank_name[:-4]  # 去掉.csv后缀存储
        bank_path = os.path.join('./questions-bank', file_name)
        if os.path.exists(bank_path):
            os.remove(bank_path)
        
        flash(f"题库 {bank_name} 已删除", "success")
    except Exception as e:
        flash(f"删除题库时出错: {str(e)}", "error")
    
    return redirect(url_for('banks.banks'))

@banks_bp.route('/switch_bank', methods=['POST'])
@login_required
def switch_bank():
    """AJAX切换当前题库 - 修复cookie删除问题"""
    user_id = get_user_id()
    
    bank_id = request.form.get('bank_id')
    if not bank_id or not bank_id.isdigit():
        return jsonify({'success': False, 'error': '无效的题库ID'})
    
    bank_id = int(bank_id)
    
    try:
        # 记录当前cookie状态
        from ..utils.cookie import cookie_logger
        old_seq_qid = request.cookies.get('current_seq_qid')
        old_bank_id = request.cookies.get('current_bank_id')
        # cookie_logger.info(f"[switch_bank] 切换前: seq_qid={old_seq_qid}, bank_id={old_bank_id}")
        # cookie_logger.info(f"[switch_bank] 切换到: bank_id={bank_id}")
        
        # 获取新cookie
        cookies = switch_current_bank(user_id, bank_id)
        cookie_logger.info(f"[switch_bank] 新cookies: {cookies}")
        
        # 创建响应
        response = jsonify({
            'success': True,
            'message': '题库切换成功',
            'bank_id': bank_id,
            'old_seq_qid': old_seq_qid,
            'old_bank_id': old_bank_id
        })
        
        # 删除旧的current_seq_qid cookie
        from ..utils.cookie import delete_cookie, set_cookies_from_dict
        
        # 使用delete_cookie（设置过期）
        response = delete_cookie(response, 'current_seq_qid')
        cookie_logger.info(f"[switch_bank] 删除current_seq_qid")
        
        # 设置新cookie
        response = set_cookies_from_dict(response, cookies)
        
        # 记录响应头
        cookie_headers = [h for h in response.headers if h[0] == 'Set-Cookie']
        cookie_logger.info(f"[switch_bank] Set-Cookie头数: {len(cookie_headers)}")
        
        return response
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)})
    except Exception as e:
        db_logger.error(f"切换题库失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'切换题库失败: {str(e)}'})