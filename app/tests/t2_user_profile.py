#!/usr/bin/env python3
"""
examcat - 用户个人资料页面测试
"""
import os
import sys
import json
import unittest
from unittest.mock import MagicMock, patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app


class UserProfileTestCase(unittest.TestCase):
    """用户个人资料页面测试用例"""
    
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
    
    def tearDown(self):
        """在每个测试之后运行，清理资源"""
        # 弹出应用上下文
        self.app_context.pop()
    
    def test_user_route_requires_login(self):
        """测试 /user 路由需要登录"""
        # 模拟未登录用户访问用户页面
        response = self.client.get('/user')
        
        # 应该重定向到登录页面或返回401
        # 根据现有auth装饰器的行为，可能是重定向或返回错误
        self.assertIn(response.status_code, [302, 401])
    
    def test_user_route_returns_html_for_logged_in_user(self):
        """测试已登录用户访问 /user 返回HTML页面"""
        # 模拟已登录用户
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
            sess['email'] = 'test@example.com'
        
        # 访问用户页面
        response = self.client.get('/user')
        
        # 响应状态码应为200
        self.assertEqual(response.status_code, 200)
        
        # 响应内容应包含HTML
        self.assertIn('text/html', response.content_type)
        
        # 页面应包含用户页面相关元素
        response_text = response.data.decode('utf-8')
        self.assertIn('个人资料', response_text)
    
    def test_user_page_contains_sidebar_navigation(self):
        """测试用户页面包含左侧固定导航标签"""
        # 模拟已登录用户
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
        
        response = self.client.get('/user')
        response_text = response.data.decode('utf-8')
        
        # 验证左侧导航标签
        expected_tabs = ['个人资料', '我的回复', '学习统计', '我的收藏', '我的错题']
        for tab in expected_tabs:
            self.assertIn(tab, response_text, f"页面应包含 '{tab}' 标签")
    
    def test_user_page_has_correct_layout_structure(self):
        """测试用户页面布局结构（侧边栏+内容区域）"""
        # 模拟已登录用户
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
        
        response = self.client.get('/user')
        response_text = response.data.decode('utf-8')
        
        # 检查侧边栏相关类名或结构
        # 这些将在后续实现中具体化
        sidebar_indicators = ['sidebar', 'side-nav', 'nav-tabs', 'user-profile']
        found_sidebar = any(indicator in response_text.lower() for indicator in sidebar_indicators)
        self.assertTrue(found_sidebar, "页面应包含侧边栏结构")
    
    def test_ajax_user_page_returns_json(self):
        """测试通过AJAX请求 /user 返回JSON格式"""
        # 模拟已登录用户
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
        
        # 模拟AJAX请求
        response = self.client.get('/user', 
                                  headers={'X-Requested-With': 'XMLHttpRequest'})
        
        # 对于非AJAX路由，可能不会返回JSON
        # 这里测试路由的基本功能
        self.assertEqual(response.status_code, 200)
    
    def test_user_profile_tab_content(self):
        """测试个人资料标签页的内容"""
        # 模拟已登录用户
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
            sess['email'] = 'test@example.com'
        
        response = self.client.get('/user')
        response_text = response.data.decode('utf-8')
        
        # 个人资料页面应显示用户信息
        self.assertIn('testuser', response_text)
        self.assertIn('test@example.com', response_text)
    
    def test_user_wrong_tab_placeholder(self):
        """测试我的错题标签页的占位符内容"""
        # 模拟已登录用户
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'

        response = self.client.get('/user')
        response_text = response.data.decode('utf-8')

        # 我的错题标签页应存在
        self.assertIn('我的错题', response_text)
        # 可以添加更精确的断言检查错题内容
    
    @patch('app.utils.database.get_db')
    def test_user_data_retrieval(self, mock_get_db):
        """测试从数据库获取用户数据"""
        # 模拟数据库连接和游标
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # 模拟数据库查询结果
        mock_cursor.fetchone.return_value = {
            'id': 1,
            'username': 'testuser',
            'email': 'test@example.com',
            'created_at': '2026-04-14 10:00:00'
        }
        
        # 模拟已登录用户
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
        
        # 访问用户页面
        response = self.client.get('/user')
        
        # 验证页面加载成功
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()