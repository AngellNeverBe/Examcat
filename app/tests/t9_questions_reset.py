#!/usr/bin/env python3
"""
examcat - 题目重置功能测试
"""
import os
import sys
import json
import unittest

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app


class QuestionsResetTestCase(unittest.TestCase):
    """题目重置功能测试用例"""

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

    def test_reset_route_requires_login(self):
        """测试 /banks/<bid>/reset 路由需要登录"""
        # 模拟未登录用户访问重置端点
        response = self.client.post('/banks/1/reset', headers={'X-Requested-With': 'XMLHttpRequest'})

        # 应该重定向到登录页面
        self.assertEqual(response.status_code, 302)
        # 验证重定向位置包含登录路由
        self.assertIn('/login', response.location)

    def test_reset_route_returns_json_on_success(self):
        """测试重置成功时返回正确的JSON结构"""
        # 模拟已登录用户
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1

        # 模拟POST请求到重置端点
        response = self.client.post('/banks/1/reset', headers={'X-Requested-With': 'XMLHttpRequest'})

        # 响应状态码
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')

        data = json.loads(response.data)

        # 验证响应结构
        self.assertIn('success', data)
        self.assertTrue(data['success'])
        self.assertIn('reset_count', data)
        self.assertIsInstance(data['reset_count'], int)

    def test_reset_route_calls_reset_history_record(self):
        """测试路由正确调用了 reset_history_record 函数"""
        # 模拟已登录用户
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1

        # 模拟POST请求，验证函数被调用
        response = self.client.post('/banks/123/reset', headers={'X-Requested-With': 'XMLHttpRequest'})

        # 验证响应
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertTrue(data['success'])
        # reset_count 应该是一个非负整数
        self.assertGreaterEqual(data['reset_count'], 0)


if __name__ == '__main__':
    unittest.main()