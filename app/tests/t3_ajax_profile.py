#!/usr/bin/env python3
"""
examcat - AJAX个人资料页面测试
"""
import os
import sys
import json
import unittest
from unittest.mock import MagicMock, patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app


class AjaxProfileTestCase(unittest.TestCase):
    """AJAX个人资料页面测试用例"""
    
    def setUp(self):
        """在每个测试之前运行，创建测试应用和测试客户端"""
        # 创建测试应用，使用测试配置
        self.app = create_app('development')
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['DATABASE_PATH'] = ':memory:'  # 使用内存数据库进行测试
        
        self.client = self.app.test_client()
        
        # 创建应用上下文
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # 初始化测试数据库
        with self.app.app_context():
            from app.utils.database import init_db
            init_db()
            
            # 插入测试数据
            from app.utils.database import get_db
            conn = get_db()
            c = conn.cursor()
            
            # 插入测试用户
            c.execute('INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                     ('testuser', 'test@example.com', 'hash'))
            conn.commit()
            
            # 不插入题库和题目，测试无当前题库的情况
    
    def tearDown(self):
        """在每个测试之后运行，清理资源"""
        # 弹出应用上下文
        self.app_context.pop()
    
    def test_ajax_profile_requires_login(self):
        """测试 /ajax/user 路由需要登录"""
        # 模拟未登录用户访问AJAX个人页面
        response = self.client.get('/ajax/user', 
                                  headers={'X-Requested-With': 'XMLHttpRequest'})
        
        # 应该返回401或重定向
        self.assertIn(response.status_code, [401, 302])
    
    def test_ajax_profile_returns_json_for_logged_in_user(self):
        """测试已登录用户访问 /ajax/user 返回JSON格式"""
        # 模拟已登录用户
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
            sess['email'] = 'test@example.com'
        
        # 模拟AJAX请求
        response = self.client.get('/ajax/user', 
                                  headers={'X-Requested-With': 'XMLHttpRequest'})
        
        # 响应状态码应为200
        self.assertEqual(response.status_code, 200)
        
        # 响应内容应为JSON
        self.assertIn('application/json', response.content_type)
        
        # 解析JSON响应
        data = json.loads(response.data.decode('utf-8'))
        
        # 验证JSON结构
        self.assertTrue(data.get('success', False))
        self.assertIn('html', data)
        self.assertIn('styles', data)
        self.assertIn('scripts', data)
        self.assertIn('title', data)
        
        # 验证HTML内容包含关键元素
        html = data['html']
        self.assertIn('个人资料', html)
        self.assertIn('testuser', html)
    
    def test_ajax_profile_contains_all_template_variables(self):
        """测试AJAX个人页面模板包含所有必需的变量"""
        # 模拟已登录用户
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
            sess['email'] = 'test@example.com'
        
        # 模拟AJAX请求
        response = self.client.get('/ajax/user', 
                                  headers={'X-Requested-With': 'XMLHttpRequest'})
        
        data = json.loads(response.data.decode('utf-8'))
        html = data['html']
        
        # 验证模板变量是否存在（通过检查生成的HTML）
        # 总体正确率变量应该被渲染
        self.assertNotIn('Undefined', html)  # 确保没有未定义变量错误
        
        # 检查关键统计元素
        stat_indicators = ['总体正确率', '已答题目', '错题数量', '学习统计']
        for indicator in stat_indicators:
            self.assertIn(indicator, html, f"页面应包含 '{indicator}'")
    
    def test_ajax_profile_without_ajax_header_redirects(self):
        """测试非AJAX请求 /ajax/user 重定向到完整页面"""
        # 模拟已登录用户
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
        
        # 非AJAX请求
        response = self.client.get('/ajax/user')
        
        # 应该重定向到完整用户页面
        self.assertEqual(response.status_code, 302)
        self.assertIn('/user', response.location)
    
    def test_ajax_profile_handles_no_current_bank(self):
        """测试没有当前题库时的AJAX个人页面处理"""
        # 模拟已登录用户（没有当前题库）
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
            sess['email'] = 'test@example.com'
        
        # 删除可能存在的当前题库cookie
        self.client.set_cookie('localhost', 'current_bank', '')
        
        # 模拟AJAX请求
        response = self.client.get('/ajax/user', 
                                  headers={'X-Requested-With': 'XMLHttpRequest'})
        
        # 即使没有当前题库，页面也应该加载成功
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data.decode('utf-8'))
        self.assertTrue(data.get('success', False))
        
        # 检查页面仍然渲染（统计部分可能显示0）
        html = data['html']
        self.assertIn('个人资料', html)


if __name__ == '__main__':
    unittest.main()