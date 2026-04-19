"""
examcat - 考试路由蓝图
"""
import os
from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from datetime import datetime, timedelta
import json
from ..utils.auth import login_required, get_user_id
from ..utils.questions import fetch_question, get_random_question_ids
from ..utils.banks import get_current_bank_id
from ..utils.exams import get_last_unfinished_exam, get_recent_exams
from ..utils.database import get_db, db_logger, add_history_record

exams_bp = Blueprint('exams', __name__, template_folder='../templates/base')

@exams_bp.route('/start_exam', methods=['POST'])
@login_required
def start_exam():
    """
    新建考试项目
    """
    user_id = get_user_id()

    # 检查是否为AJAX请求
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
              request.headers.get('X-Ajax-Navigation') == 'true'

    # 获取请求参数
    question_count = int(request.form.get('question_count', 10))
    
    # 获取当前题库并抽取题目
    current_bank_result = get_current_bank_id(user_id)
    if not current_bank_result or current_bank_result[0] is None:
        if is_ajax:
            return jsonify({
                'success': False,
                'message': '未找到可用题库',
                'category': 'error'
            }), 400
        else:
            flash("未找到可用题库", "error")
            return redirect(url_for('exams.exams_index'))
    current_bank = current_bank_result[0]
    question_ids = get_random_question_ids(question_count, user_id)

    if not question_ids:
        if is_ajax:
            return jsonify({
                'success': False,
                'message': '当前题库中没有足够的题目',
                'category': 'error'
            }), 400
        else:
            flash("当前题库中没有足够的题目", "error")
            return redirect(url_for('exams.exams_index'))
    
    # 初始化考试数据
    start_time = datetime.now()
    answers = []  # 已答题目答案列表
    elapsed_time = 0  # 已用时间（秒）
    completed = 0  # 是否完成（0=未完成，1=已完成）
    score = 0.0  # 初始分数
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        # 插入新的考试记录，restart_at 初始等于 start_at
        c.execute('''
            INSERT INTO exams 
            (user_id, question_ids, bank_id, start_at, restart_at, duration, answers, complete, score) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            json.dumps(question_ids),
            current_bank,
            start_time,
            start_time,  # restart_at 初始等于 start_at
            0,
            json.dumps(answers),
            completed,
            score
        ))
        exam_id = c.lastrowid
        conn.commit()
        db_logger.info(f"[{os.getpid()}] Add exam: 用户{user_id}, ID{exam_id}")

        if is_ajax:
            # 返回JSON响应，指示导航到考试页面
            return jsonify({
                'success': True,
                'message': '考试创建成功',
                'category': 'success',
                'redirect': url_for('exams.exam_main', exam_id=exam_id),
                'ajax_navigate': True,
                'exam_id': exam_id
            })
        else:
            # 重定向到考试主函数
            return redirect(url_for('exams.exam_main', exam_id=exam_id))
        
    except Exception as e:
        conn.rollback()
        if is_ajax:
            return jsonify({
                'success': False,
                'message': f'启动考试失败: {str(e)}',
                'category': 'error'
            }), 500
        else:
            flash(f"启动考试失败: {str(e)}", "error")
            return redirect(url_for('exams.exams_index'))

@exams_bp.route('/exams/<int:exam_id>', methods=['GET', 'POST'])
@login_required
def exam_main(exam_id):
    """
    考试主页面
    """
    user_id = get_user_id()
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
        flash("考试不存在或无权访问", "error")
        return redirect(url_for('exams.exams_index'))
    
    if request.method == 'GET':
        # GET请求：显示考试页面
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
        
        return render_template('exam.html', 
                              exam=exam, 
                              questions=questions,
                              elapsed_time=elapsed_time,
                              exam_id=exam_id)
    
    else:
        # POST请求：处理保存或提交
        action = request.form.get('action', 'save')  # 'save' 或 'submit'
        
        # 获取所有题目的答案
        question_ids = json.loads(exam['question_ids'])
        new_answers = []
        
        for qid in question_ids:
            user_answer = request.form.getlist(f'answer_{qid}')
            answer_str = "".join(sorted(user_answer)) if user_answer else ""
            new_answers.append(answer_str)
        
        # 计算当前时间与 restart_at 的差值，累加到 duration
        restart_time = datetime.strptime(exam['restart_at'], '%Y-%m-%d %H:%M:%S.%f')
        current_time = datetime.now()
        session_duration = int((current_time - restart_time).total_seconds())
        total_duration = exam['duration'] + session_duration
        
        if action == 'submit':
            # 提交考试：计算分数并标记完成
            correct_count = 0
            total = len(question_ids)
            
            for idx, qid in enumerate(question_ids):
                q = fetch_question(qid)
                if not q:
                    continue
                    
                user_answer_str = new_answers[idx]
                correct_answer_str = "".join(sorted(q.get('answer', '')))
                correct = int(user_answer_str == correct_answer_str)
                bank_id = q['bank_id']

                add_history_record(user_id, qid, user_answer_str, correct, bank_id)
                # 保存到答题历史
                db_logger.info(f"[{os.getpid()}] Add history: 用户{user_id}, 题目{qid}, 答案{user_answer_str}, 正确{correct}")
                correct_count += correct
            
            # 计算分数
            score = (correct_count / total * 100) if total > 0 else 0
            completed = 1
            
            # 更新考试记录：答案、duration、complete、score，restart_at 保持不变
            c.execute('''
                UPDATE exams 
                SET answers = ?, duration = ?, complete = ?, score = ?
                WHERE id = ?
            ''', (
                json.dumps(new_answers),
                total_duration,
                completed,
                score,
                exam_id
            ))
            db_logger.info(f"[{os.getpid()}] Submit exam: 用户{user_id}, ID{exam_id}, 完成{completed}")
            conn.commit()
            
            # 判断是否为AJAX请求
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                      request.headers.get('X-Ajax-Navigation') == 'true'
            
            if is_ajax:
                # 返回JSON响应
                return jsonify({
                    'success': True,
                    'message': f'考试提交成功！正确率：{correct_count}/{total} = {score:.2f}%',
                    'category': 'success',
                    'correct_count': correct_count,
                    'total': total,
                    'score': round(score, 2),
                    'completed': True,
                    'exam_id': exam_id
                })
            else:
                flash(f"考试提交成功！正确率：{correct_count}/{total} = {score:.2f}%", "success")
                return redirect(url_for('exams.exam_main', exam_id=exam_id))
            
        else:
            # 保存答案：不计算分数，不标记完成
            # 更新 restart_at 为当前时间（重置会话开始时间）
            c.execute('''
                UPDATE exams 
                SET answers = ?, duration = ?, restart_at = ?
                WHERE id = ?
            ''', (
                json.dumps(new_answers),
                total_duration,
                current_time,
                exam_id
            ))
            db_logger.info(f"[{os.getpid()}] Save exam: 用户{user_id}, ID{exam_id}, 完成0")
            conn.commit()
            
            # 修改：返回包含flash消息的JSON
            return jsonify({
                'success': True,
                'message': '答案已保存',
                'category': 'info',
                'saved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'saved_answers': new_answers
            })

@exams_bp.route('/continue_exam/<int:exam_id>')
@login_required
def continue_exam(exam_id):
    """
    继续考试
    加载对应id的考试内容，返回已答题目答案，返回已用时间，
    重定向到main（/exam/<id>）
    """
    # 检查是否为AJAX请求
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
              request.headers.get('X-Ajax-Navigation') == 'true'

    user_id = get_user_id()
    conn = get_db()
    c = conn.cursor()
    
    # 获取考试记录
    c.execute('''
        SELECT * FROM exams 
        WHERE id = ? AND user_id = ? AND complete = 0
    ''', (exam_id, user_id))
    
    exam = c.fetchone()

    if not exam:
        if is_ajax:
            return jsonify({
                'success': False,
                'message': '考试不存在、已完成或无权访问',
                'category': 'error'
            }), 404
        else:
            flash("考试不存在、已完成或无权访问", "error")
            return redirect(url_for('exams.exams_index'))
    
    # 计算已用时间
    start_time = datetime.strptime(exam['start_at'], '%Y-%m-%d %H:%M:%S.%f')
    current_time = datetime.now()
    elapsed_time = int((current_time - start_time).total_seconds())
    
    # 获取已保存的答案
    answers = json.loads(exam['answers']) if exam['answers'] else []
    
    # 这里可以将答案和已用时间存入session，供exam_main使用
    session['continue_exam_data'] = {
        'exam_id': exam_id,
        'answers': answers,
        'elapsed_time': elapsed_time
    }
    
    if is_ajax:
        # 返回JSON响应，指示导航到考试页面
        return jsonify({
            'success': True,
            'message': '继续考试',
            'category': 'info',
            'redirect': url_for('exams.exam_main', exam_id=exam_id),
            'ajax_navigate': True,
            'exam_id': exam_id
        })
    else:
        # 重定向到考试主页面
        return redirect(url_for('exams.exam_main', exam_id=exam_id))

@exams_bp.route('/exam/detail/<int:exam_id>')
@login_required
def exam_detail(exam_id):
    """获取考试详情"""
    user_id = get_user_id()
    conn = get_db()
    c = conn.cursor()
    
    # 获取考试基本信息 - 修复：包含所有需要的列
    c.execute('''
        SELECT 
            id,
            question_ids,         -- 添加：题目ID列表
            answers,              -- 添加：答案列表
            start_at,
            duration,
            complete,
            score,
            json_array_length(question_ids) as question_count
        FROM exams 
        WHERE id = ? AND user_id = ?
    ''', (exam_id, user_id))
    
    exam = c.fetchone()
    
    if not exam:
        return jsonify({
            "success": False,
            "msg": "考试不存在或无权访问"
        }), 404
    
    # 调试信息：打印可用的列
    print(f"Available columns: {list(exam.keys())}")
    
    # 获取考试结果详情（如果有的话）
    results = []
    
    # 检查question_ids是否存在
    if exam['question_ids']:
        try:
            question_ids = json.loads(exam['question_ids'])
            
            # 检查answers是否存在
            answers = json.loads(exam['answers']) if exam['answers'] else []
            
            if exam['complete'] and exam['score'] is not None:
                for idx, qid in enumerate(question_ids):
                    q = fetch_question(qid)
                    if q:
                        user_answer = answers[idx] if idx < len(answers) else ''
                        correct_answer = q.get('answer', '')
                        
                        # 确保比较的字符串格式一致
                        if isinstance(user_answer, list):
                            user_answer_str = "".join(sorted(user_answer))
                        else:
                            user_answer_str = user_answer
                            
                        if isinstance(correct_answer, list):
                            correct_answer_str = "".join(sorted(correct_answer))
                        else:
                            correct_answer_str = correct_answer
                        
                        is_correct = user_answer_str == correct_answer_str
                        
                        results.append({
                            "id": qid,
                            "stem": q.get('stem', ''),
                            "user_answer": user_answer_str,
                            "correct_answer": correct_answer_str,
                            "is_correct": is_correct
                        })
        except json.JSONDecodeError as e:
            print(f"JSON解码错误: {e}")
            results = []
    else:
        question_ids = []
    
    # 格式化数据
    formatted_duration = "00:00:00"
    if exam['duration']:
        hours = exam['duration'] // 3600
        minutes = (exam['duration'] % 3600) // 60
        seconds = exam['duration'] % 60
        formatted_duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    # 确定得分CSS类
    score_class = ""
    if exam['score']:
        if exam['score'] < 60:
            score_class = "text-danger"
        elif exam['score'] < 80:
            score_class = "text-warning"
        else:
            score_class = "text-success"
    
    return jsonify({
        "success": True,
        "exam": {
            "id": exam['id'],
            "start_time": exam['start_at'],
            "duration": exam['duration'],
            "formatted_duration": formatted_duration,
            "completed": bool(exam['complete']),
            "score": exam['score'],
            "score_class": score_class,
            "question_count": exam['question_count'],
            "results": results
        }
    })

@exams_bp.route('/exams', methods=['GET', 'POST'])
@login_required
def exams_index():
    """考试主页面 - 左侧开始考试，右侧考试历史"""
    user_id = get_user_id()

    # 检查是否为AJAX请求
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
              request.headers.get('X-Ajax-Navigation') == 'true'

    if request.method == 'POST':
        # 处理开始考试请求
        question_count = int(request.form.get('question_count', 20))

        # 获取当前题库并抽取题目
        current_bank_result = get_current_bank_id(user_id)
        if not current_bank_result or current_bank_result[0] is None:
            if is_ajax:
                return jsonify({
                    'success': False,
                    'message': '未找到可用题库',
                    'category': 'error'
                }), 400
            else:
                flash("未找到可用题库", "error")
                return redirect(url_for('exams.exams_index'))
        current_bank = current_bank_result[0]
        question_ids = get_random_question_ids(question_count, user_id)

        if not question_ids:
            if is_ajax:
                return jsonify({
                    'success': False,
                    'message': '当前题库中没有足够的题目',
                    'category': 'error'
                }), 400
            else:
                flash("当前题库中没有足够的题目", "error")
                return redirect(url_for('exams.exams_index'))

        # 初始化考试数据
        start_time = datetime.now()
        answers = []
        elapsed_time = 0
        completed = 0
        score = 0.0

        conn = get_db()
        c = conn.cursor()

        try:
            c.execute('''
                INSERT INTO exams
                (user_id, question_ids, bank_id, start_at, restart_at, duration, answers, complete, score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                json.dumps(question_ids),
                current_bank,
                start_time,
                start_time,
                0,
                json.dumps(answers),
                completed,
                score
            ))
            exam_id = c.lastrowid
            conn.commit()
            db_logger.info(f"[{os.getpid()}] Add exam: 用户{user_id}, ID{exam_id}")

            if is_ajax:
                # 返回JSON响应，指示导航到考试页面
                return jsonify({
                    'success': True,
                    'message': '考试创建成功',
                    'category': 'success',
                    'redirect': url_for('exams.exam_main', exam_id=exam_id),
                    'ajax_navigate': True,
                    'exam_id': exam_id
                })
            else:
                # 重定向到考试页面
                return redirect(url_for('exams.exam_main', exam_id=exam_id))

        except Exception as e:
            conn.rollback()
            if is_ajax:
                return jsonify({
                    'success': False,
                    'message': f'启动考试失败: {str(e)}',
                    'category': 'error'
                }), 500
            else:
                flash(f"启动考试失败: {str(e)}", "error")
                return redirect(url_for('exams.exams_index'))

    # GET请求：显示考试主页
    last_unfinished = get_last_unfinished_exam(user_id)
    recent_exams = get_recent_exams(user_id, limit=8)

    return render_template('exams.html',
                          last_unfinished_exam=last_unfinished,
                          recent_exams=recent_exams)
