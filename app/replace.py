#!/usr/bin/env python3
"""
URL_FOR替换脚本 - 将原url_for调用替换为蓝图格式
"""

import os
import re

# 定义替换映射
replacements = {
    # 认证相关
    r"url_for\('login'": "url_for('auth.login'",
    r"url_for\('register'": "url_for('auth.register'",
    r"url_for\('logout'": "url_for('auth.logout'",
    
    # 主页面相关
    r"url_for\('index'": "url_for('main.index'",
    r"url_for\('modes'": "url_for('main.modes'",
    
    # 题目相关
    r"url_for\('random_question'": "url_for('questions.random_question'",
    r"url_for\('show_question'": "url_for('questions.show'",
    r"url_for\('show_history'": "url_for('questions.show_history'",
    r"url_for\('search'": "url_for('questions.search'",
    r"url_for\('wrong_questions'": "url_for('questions.wrong_questions'",
    r"url_for\('only_wrong_mode'": "url_for('questions.only_wrong_mode'",
    r"url_for\('sequential_start'": "url_for('questions.sequential_start'",
    r"url_for\('show_sequential_question'": "url_for('questions.show_sequential_question'",
    
    # 题库相关
    r"url_for\('select_bank'": "url_for('banks.select_bank'",
    r"url_for\('load_bank'": "url_for('banks.load_bank'",
    r"url_for\('upload_bank'": "url_for('banks.upload_bank'",
    r"url_for\('delete_bank'": "url_for('banks.delete_bank'",
    
    # 考试相关
    r"url_for\('start_timed_mode'": "url_for('exams.start_timed'",
    r"url_for\('timed_mode'": "url_for('exams.timed_mode'",
    r"url_for\('submit_timed_mode'": "url_for('exams.submit_timed_mode'",
    r"url_for\('start_exam'": "url_for('exams.start_exam'",
    r"url_for\('exam'": "url_for('exams.exam'",
    r"url_for\('submit_exam'": "url_for('exams.submit_exam'",
    
    # 统计相关
    r"url_for\('statistics'": "url_for('statistics.show'",
    
    # 收藏相关
    r"url_for\('favorite_question'": "url_for('favorites.add'",
    r"url_for\('unfavorite_question'": "url_for('favorites.remove'",
    r"url_for\('update_tag'": "url_for('favorites.update_tag'",
    r"url_for\('show_favorites'": "url_for('favorites.show'",
    
    # 浏览相关
    r"url_for\('browse_questions'": "url_for('browse.index'",
    r"url_for\('filter_questions'": "url_for('browse.filter'",
}

def replace_in_file(filepath):
    """替换文件中的url_for调用"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    for pattern, replacement in replacements.items():
        content = re.sub(pattern, replacement, content)
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"已修改: {filepath}")
        return True
    return False

def process_directory(directory, extensions=('.py', '.html')):
    """处理目录下的所有文件"""
    modified_count = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(extensions):
                filepath = os.path.join(root, file)
                if replace_in_file(filepath):
                    modified_count += 1
    
    print(f"总共修改了 {modified_count} 个文件")

if __name__ == '__main__':
    # 处理当前目录下的所有.py和.html文件
    process_directory('.')