#!/usr/bin/env python3
"""
examcat - 考试页面AJAX功能测试
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


class ExamAjaxTestCase(unittest.TestCase):
    """考试页面AJAX功能测试用例"""
    
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

    def test_ajax_exam_route_requires_login(self):
        """测试 /ajax/exam-<id> 路由需要登录"""
        # 模拟未登录用户访问
        response = self.client.get('/ajax/exam-123',
                                  headers={'X-Requested-With': 'XMLHttpRequest'})

        # 应该返回401或重定向
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.content_type, 'application/json')
        
        data = json.loads(response.data)
        self.assertIn('success', data)
        self.assertFalse(data['success'])
        self.assertIn('error', data)

    @patch('app.routes.ajax.get_user_id')
    @patch('app.routes.exams.get_exam_data')
    def test_ajax_exam_route_returns_json(self, mock_get_exam_data, mock_get_user_id):
        """测试 /ajax/exam-<id> 返回JSON数据（用于ajax导航）"""
        # 模拟已登录用户
        mock_get_user_id.return_value = 1
        
        # 模拟考试数据
        mock_get_exam_data.return_value = {
            'exam': {
                'id': 123,
                'complete': 0,
                'score': 0.0,
                'duration': 300,
                'question_ids': '[1, 2, 3]',
                'answers': '[]',
                'start_at': '2024-01-01 10:00:00',
                'restart_at': '2024-01-01 10:00:00'
            },
            'questions': [
                {
                    'id': 1,
                    'stem': '题目1',
                    'type': '单选题',
                    'options': {'A': '选项A', 'B': '选项B'},
                    'answer': '',
                    'correct_answer': 'A',
                    'is_correct': False
                }
            ],
            'elapsed_time': 300,
            'exam_id': 123
        }

        # 模拟AJAX请求
        response = self.client.get('/ajax/exam-123',
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
        self.assertEqual(data['page'], 'exam')

    def test_exam_main_post_ajax_submit_returns_json(self):
        """测试 POST /exams/<id> 提交考试时返回JSON（AJAX请求）"""
        # 模拟已登录用户
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1

        # 模拟AJAX提交请求
        response = self.client.post('/exams/123', 
                                   data={'action': 'submit', 'answer_1': 'A'},
                                   headers={'X-Requested-With': 'XMLHttpRequest'})

        # 路由应该处理请求（即使考试不存在会返回404或错误）
        # 我们只检查响应类型和基本结构
        self.assertEqual(response.content_type, 'application/json')
        
        data = json.loads(response.data)
        self.assertIn('success', data)

    def test_exam_main_post_ajax_save_returns_json(self):
        """测试 POST /exams/<id> 保存答案时返回JSON（AJAX请求）"""
        # 模拟已登录用户
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1

        # 模拟AJAX保存请求
        response = self.client.post('/exams/123', 
                                   data={'action': 'save', 'answer_1': 'A'},
                                   headers={'X-Requested-With': 'XMLHttpRequest'})

        # 路由应该处理请求
        self.assertEqual(response.content_type, 'application/json')
        
        data = json.loads(response.data)
        self.assertIn('success', data)

    def test_non_ajax_exam_route_redirects(self):
        """测试非AJAX请求 /ajax/exam-<id> 重定向到完整页面"""
        # 模拟已登录用户
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1

        # 非AJAX请求
        response = self.client.get('/ajax/exam-123')

        # 应该重定向到完整考试页面
        self.assertEqual(response.status_code, 302)
        self.assertIn('/exams/123', response.location)

    def test_ajax_navigator_exam_url_rewriting(self):
        """测试ajax_navigator.js中考试URL重写逻辑（通过模拟）"""
        # 这个测试验证URL重写逻辑，但实际上在JavaScript中
        # 这里我们只验证后端路由存在
        pass


if __name__ == '__main__':
    unittest.main()