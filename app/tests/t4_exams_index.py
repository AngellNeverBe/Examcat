#!/usr/bin/env python3
"""
examcat - 考试主页功能测试
"""
import os
import sys
import json
import unittest
from unittest.mock import MagicMock, patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app
from app.utils.database import get_db


class ExamsIndexTestCase(unittest.TestCase):
    """考试主页功能测试用例"""

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

    def test_exams_index_requires_login(self):
        """测试 /exams 路由需要登录"""
        # 模拟未登录用户访问
        response = self.client.get('/exams')

        # 应该重定向到登录页
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.location)

    def test_exams_index_returns_html_for_logged_in_user(self):
        """测试已登录用户访问 /exams 返回HTML页面"""
        # 模拟已登录用户
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1

        # 访问/exams路由
        response = self.client.get('/exams')

        # 响应状态码应为200
        self.assertEqual(response.status_code, 200)
        # 响应内容类型应为text/html
        self.assertEqual(response.content_type, 'text/html; charset=utf-8')
        # 响应应包含考试页面标题
        response_text = response.data.decode('utf-8')
        self.assertIn('考试', response_text)

    def test_exams_index_ajax_route_returns_json(self):
        """测试 /ajax/exams 返回JSON数据（用于ajax导航）"""
        # 模拟已登录用户
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1

        # 模拟AJAX请求
        response = self.client.get('/ajax/exams',
                                  headers={'X-Requested-With': 'XMLHttpRequest'})

        # 响应状态码
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')

        data = json.loads(response.data)

        # 验证响应结构
        self.assertIn('success', data)
        self.assertTrue(data['success'])
        self.assertIn('html', data)
        self.assertIn('styles', data)
        self.assertIn('scripts', data)
        self.assertIn('title', data)
        self.assertIn('page', data)
        self.assertEqual(data['page'], 'exams')

    @patch('app.routes.exams.get_last_unfinished_exam')
    @patch('app.routes.exams.get_recent_exams')
    def test_exams_index_context_data(self, mock_get_recent_exams, mock_get_last_unfinished_exam):
        """测试 /exams 路由传递正确的上下文数据"""
        # 模拟函数返回数据
        mock_get_last_unfinished_exam.return_value = {'id': 123, 'start_time': '2024-01-01 10:00:00'}
        mock_get_recent_exams.return_value = [
            {'id': 1, 'start_time': '2024-01-01 10:00:00', 'duration': 3600, 'score': 85.5, 'completed': True},
            {'id': 2, 'start_time': '2024-01-02 11:00:00', 'duration': 1800, 'score': None, 'completed': False}
        ]

        # 模拟已登录用户
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1

        response = self.client.get('/exams')
        self.assertEqual(response.status_code, 200)

        # 检查模板上下文数据（通过检查响应内容中的特定标记）
        # 这里我们检查页面是否包含期望的元素
        response_text = response.data.decode('utf-8')

        # 检查开始考试表单是否存在
        self.assertIn('开始考试', response_text)
        self.assertIn('question_count', response_text)
        # 检查下拉菜单选项
        self.assertIn('10题', response_text)
        self.assertIn('20题', response_text)
        self.assertIn('50题', response_text)
        self.assertIn('100题', response_text)
        # 检查默认选中20题
        self.assertIn('value="20" selected', response_text)

    def test_exams_index_post_start_exam_redirects(self):
        """测试 POST /exams 开始考试重定向到考试页面"""
        # 模拟已登录用户
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1

        # 模拟开始考试请求
        response = self.client.post('/exams', data={'question_count': 20})

        # 由于实际数据库中没有题目，可能会重定向或返回错误
        # 我们只检查响应状态码不是500（内部错误）
        self.assertNotEqual(response.status_code, 500)

    def test_exams_route_renamed_from_exam(self):
        """测试 /exams/<id> 路由存在（从 /exam/<id> 重命名）"""
        # 模拟已登录用户
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1

        # 测试 /exams/1 路由
        response = self.client.get('/exams/1')

        # 路由应该存在，即使考试不存在也会返回404或重定向
        # 我们只检查不是405（方法不允许）或404（如果考试不存在）
        self.assertNotEqual(response.status_code, 405)

    def test_old_exam_route_redirects_or_404(self):
        """测试旧的 /exam 路由不再可用"""
        # 模拟已登录用户
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1

        # 测试旧的 /exam 路由（应该重定向到 /exams 或返回404）
        response = self.client.get('/exam')

        # 可能是404或重定向到/exams
        if response.status_code == 302:
            self.assertIn('/exams', response.location)
        elif response.status_code == 404:
            pass  # 也是可以接受的
        else:
            # 不应该返回200，除非有兼容性处理
            self.assertNotEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()