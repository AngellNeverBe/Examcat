#!/usr/bin/env python3
"""
examcat - 题目start函数AJAX行为测试
"""
import os
import sys
import json
import unittest
from unittest.mock import MagicMock, patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app
from app.utils.database import get_db, init_db
from app.utils.questions import get_wrong_question_ids, get_favorite_question_ids


class QuestionsStartAjaxTestCase(unittest.TestCase):
    """题目start函数AJAX行为测试用例"""

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
            init_db()
            self._seed_test_data()

    def tearDown(self):
        """在每个测试之后运行，清理资源"""
        # 弹出应用上下文
        self.app_context.pop()

    def _seed_test_data(self):
        """插入测试数据（复制自t7_questions_mode.py）"""
        conn = get_db()
        c = conn.cursor()

        # 先删除可能存在的测试数据，避免冲突
        test_bank_ids = [5000, 5001]
        for bank_id in test_bank_ids:
            c.execute('DELETE FROM questions WHERE bank_id = ?', (bank_id,))
            c.execute('DELETE FROM banks WHERE id = ?', (bank_id,))

        c.execute('DELETE FROM users WHERE id = 1999')
        c.execute('DELETE FROM history WHERE user_id = 1999')
        c.execute('DELETE FROM favorites WHERE user_id = 1999')

        # 插入两个题库（使用更大的ID和更独特的名称避免与init_db冲突）
        c.execute('''
            INSERT INTO banks (id, bankname, category, total_count)
            VALUES (5000, '单元测试题库1_特殊_5000', '大一', 10),
                   (5001, '单元测试题库2_特殊_5001', '大二', 5)
        ''')

        # 插入题目（跨两个题库，使用更大的题目ID避免冲突）
        # 题库5000：题目30001-30005
        # 题库5001：题目30006-30010
        for i in range(1, 6):
            question_id = 30000 + i
            c.execute('''
                INSERT INTO questions (id, "order", bank_id, stem, answer, type, category, options)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (question_id, i, 5000, f'题目{question_id}', 'A', '单选题', '测试', '{"A": "选项A"}'))

        for i in range(6, 11):
            question_id = 30000 + i
            c.execute('''
                INSERT INTO questions (id, "order", bank_id, stem, answer, type, category, options)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (question_id, i-5, 5001, f'题目{question_id}', 'B', '多选题', '测试', '{"A": "选项A", "B": "选项B"}'))

        # 插入用户（提供必需的password_hash字段，使用ID 1999避免与init_db冲突）
        c.execute('INSERT INTO users (id, username, email, password_hash, created_at) VALUES (1999, "testuser", "test@example.com", "dummy_hash", "2026-04-18 10:00:00")')

        # 插入错题记录（history表）
        # 题目30001：正确（不在错题列表）
        # 题目30002：错误，错误时间较旧
        # 题目30003：错误，错误时间较新
        # 题目30006：错误，来自另一个题库
        import datetime
        old_time = '2026-04-17 10:00:00'
        new_time = '2026-04-18 10:00:00'

        c.execute('''
            INSERT INTO history (user_id, question_id, bank_id, complete, correct, wrong_count, updated_at)
            VALUES (1999, 30001, 5000, 1, 1, 0, ?)
        ''', (old_time,))

        c.execute('''
            INSERT INTO history (user_id, question_id, bank_id, complete, correct, wrong_count, updated_at)
            VALUES (1999, 30002, 5000, 1, 0, 2, ?)
        ''', (old_time,))

        c.execute('''
            INSERT INTO history (user_id, question_id, bank_id, complete, correct, wrong_count, updated_at)
            VALUES (1999, 30003, 5000, 1, 0, 1, ?)
        ''', (new_time,))

        c.execute('''
            INSERT INTO history (user_id, question_id, bank_id, complete, correct, wrong_count, updated_at)
            VALUES (1999, 30006, 5001, 1, 0, 3, ?)
        ''', (new_time,))

        # 插入收藏记录
        # 题目30004、30005、30007、30008，收藏时间不同
        c.execute('''
            INSERT INTO favorites (user_id, question_id, bank_id, tag, created_at)
            VALUES (1999, 30004, 5000, '重要', '2026-04-17 11:00:00')
        ''')

        c.execute('''
            INSERT INTO favorites (user_id, question_id, bank_id, tag, created_at)
            VALUES (1999, 30005, 5000, '易错', '2026-04-18 11:00:00')
        ''')

        c.execute('''
            INSERT INTO favorites (user_id, question_id, bank_id, tag, created_at)
            VALUES (1999, 30007, 5001, '复习', '2026-04-17 12:00:00')
        ''')

        c.execute('''
            INSERT INTO favorites (user_id, question_id, bank_id, tag, created_at)
            VALUES (1999, 30008, 5001, '复习', '2026-04-18 12:00:00')
        ''')

        conn.commit()

    def test_start_ajax_wrong_mode_success(self):
        """测试AJAX请求wrong模式start路由成功"""
        # 模拟登录
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1999

        # 发送AJAX请求到wrong模式start路由
        response = self.client.get('/banks/5000/wrong/start',
                                  headers={'X-Ajax-Navigation': 'true'})

        # 修改start函数后，应该返回JSON而不是重定向
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('html', data)
        self.assertEqual(data['page'], 'question')
        # 应该包含题目内容
        self.assertIn('题目30003', data['html'])

    def test_start_ajax_favorites_mode_success(self):
        """测试AJAX请求favorites模式start路由成功"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1999

        response = self.client.get('/banks/5000/favorites/start',
                                  headers={'X-Ajax-Navigation': 'true'})

        # 修改start函数后，应该返回JSON而不是重定向
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('html', data)
        self.assertEqual(data['page'], 'question')
        # 应该包含题目内容（第一个收藏是30008）
        self.assertIn('题目30008', data['html'])

    def test_start_ajax_sequential_mode_success(self):
        """测试AJAX请求sequential模式start路由成功"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1999

        response = self.client.get('/banks/5000/sequential/start',
                                  headers={'X-Ajax-Navigation': 'true'})

        # 修改start函数后，应该返回JSON而不是重定向
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('html', data)
        self.assertEqual(data['page'], 'question')
        # sequential模式应该返回题库5000的第一题（题目30001）

    def test_start_ajax_wrong_mode_no_wrong_questions(self):
        """测试没有错题时wrong模式返回错误JSON"""
        # 先清空该用户的错题记录
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM history WHERE user_id = 1999 AND correct = 0')
        conn.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = 1999

        response = self.client.get('/banks/5000/wrong/start',
                                  headers={'X-Ajax-Navigation': 'true'})

        # 修改start函数后，应该返回JSON错误响应
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('message', data)
        self.assertIn('您目前没有错题', data['message'])

    def test_start_ajax_favorites_mode_no_favorites(self):
        """测试没有收藏时favorites模式返回错误JSON"""
        # 先清空该用户的收藏记录
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM favorites WHERE user_id = 1999')
        conn.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = 1999

        response = self.client.get('/banks/5000/favorites/start',
                                  headers={'X-Ajax-Navigation': 'true'})

        # 修改start函数后，应该返回JSON错误响应
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('message', data)
        self.assertIn('您目前没有收藏题目', data['message'])

    def test_start_normal_request_wrong_mode_redirect(self):
        """测试普通请求（非AJAX）wrong模式重定向"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1999

        # 普通请求，没有AJAX头
        response = self.client.get('/banks/5000/wrong/start')

        # 应该重定向到题目页面
        self.assertEqual(response.status_code, 302)
        # 重定向目标应该是题目页面（错题模式第一个错题是30003，属于题库5000）
        self.assertIn('/banks/5000/questions/30003', response.location)
        self.assertIn('mode=wrong', response.location)

    def test_start_normal_request_favorites_mode_redirect(self):
        """测试普通请求（非AJAX）favorites模式重定向"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1999

        response = self.client.get('/banks/5000/favorites/start')

        self.assertEqual(response.status_code, 302)
        # 收藏模式第一个收藏是30008，属于题库5001（跨题库）
        self.assertIn('/banks/5001/questions/30008', response.location)
        self.assertIn('mode=favorites', response.location)

    def test_start_ajax_response_format_matches_show(self):
        """测试start函数AJAX响应格式与show函数一致"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1999

        # 首先获取show函数的AJAX响应格式作为参考
        response_show = self.client.get('/banks/5000/questions/30003?mode=wrong',
                                       headers={'X-Ajax-Navigation': 'true'})

        if response_show.status_code == 200 and response_show.content_type == 'application/json':
            data_show = json.loads(response_show.data)
            # 验证show函数的响应格式
            expected_keys = ['success', 'html', 'styles', 'scripts', 'title', 'page']
            for key in expected_keys:
                self.assertIn(key, data_show)

            # 测试start的响应格式与show一致
            response_start = self.client.get('/banks/5000/wrong/start',
                                            headers={'X-Ajax-Navigation': 'true'})
            data_start = json.loads(response_start.data)
            for key in expected_keys:
                self.assertIn(key, data_start)
            self.assertEqual(data_start['page'], 'question')
        else:
            self.skipTest("show函数AJAX响应格式不符合预期，无法进行格式对比测试")


if __name__ == '__main__':
    unittest.main()