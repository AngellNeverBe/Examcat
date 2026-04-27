#!/usr/bin/env python3
"""
examcat - 个人资料更新测试
测试 /user/update 端点的各项功能
"""
import os
import sys
import json
import unittest
from unittest.mock import MagicMock, patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app


class ProfileUpdateTestCase(unittest.TestCase):
    """个人资料更新测试用例"""

    def setUp(self):
        """在每个测试之前运行，创建测试应用和测试客户端"""
        self.app = create_app('development')
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['DATABASE_PATH'] = ':memory:'

        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        # 初始化测试数据库
        with self.app.app_context():
            from app.utils.database import init_db, get_db
            init_db()

            conn = get_db()
            c = conn.cursor()

            # 清理残留数据并重置自增ID，确保测试隔离
            c.execute('DELETE FROM users')
            c.execute('DELETE FROM sqlite_sequence WHERE name="users"')

            # 插入测试用户（显式指定ID保证一致性）
            c.execute(
                'INSERT INTO users (id, username, email, password_hash) VALUES (?, ?, ?, ?)',
                (1, 'testuser', 'test@example.com', 'hash1'))
            c.execute(
                'INSERT INTO users (id, username, email, password_hash) VALUES (?, ?, ?, ?)',
                (2, 'otheruser', 'other@example.com', 'hash2'))
            c.execute(
                'INSERT INTO users (id, username, email, password_hash) VALUES (?, ?, ?, ?)',
                (3, 'admin', 'admin@example.com', 'hash3'))
            conn.commit()

    def tearDown(self):
        """在每个测试之后运行，清理资源"""
        self.app_context.pop()

    def _login_as(self, user_id, username, email='test@example.com', is_admin=False):
        """辅助方法：模拟登录指定用户"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['username'] = username
            sess['email'] = email
            sess['is_admin'] = is_admin

    # ========== 权限测试 ==========

    def test_update_requires_login(self):
        """测试未登录用户 POST /user/update 被拒绝"""
        response = self.client.post('/user/update',
                                    data={'username': 'newname'},
                                    content_type='application/x-www-form-urlencoded')
        self.assertIn(response.status_code, [302, 401],
                      "未登录请求应被重定向或返回401")

    # ========== 用户名修改测试 ==========

    def test_update_username_success(self):
        """测试成功修改用户名：DB和session都应更新"""
        self._login_as(1, 'testuser', 'test@example.com')

        response = self.client.post('/user/update',
                                    data={'username': 'newname'},
                                    content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data.decode('utf-8'))
        self.assertTrue(data.get('success'), f"修改应成功，实际: {data}")

        # 验证数据库已更新
        with self.app.app_context():
            from app.utils.database import get_db
            conn = get_db()
            c = conn.cursor()
            c.execute('SELECT username FROM users WHERE id = ?', (1,))
            row = c.fetchone()
            self.assertEqual(row['username'], 'newname',
                             "数据库中用户名应更新为 newname")

        # 验证 session 已更新
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('username'), 'newname',
                             "session 中用户名应更新为 newname")

    def test_update_username_duplicate(self):
        """测试修改为已存在的用户名（重复）：应被拒绝"""
        self._login_as(1, 'testuser', 'test@example.com')

        response = self.client.post('/user/update',
                                    data={'username': 'otheruser'},
                                    content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data.decode('utf-8'))
        self.assertFalse(data.get('success'),
                         "重复用户名修改应失败")
        self.assertIn('已存在', data.get('message', ''),
                      "错误信息应包含'已存在'")

        # 验证数据库未被修改
        with self.app.app_context():
            from app.utils.database import get_db
            conn = get_db()
            c = conn.cursor()
            c.execute('SELECT username FROM users WHERE id = ?', (1,))
            row = c.fetchone()
            self.assertEqual(row['username'], 'testuser',
                             "数据库中用户名不应被修改")

    def test_update_username_unchanged(self):
        """测试修改为当前用户名（不变）：应成功（幂等操作）"""
        self._login_as(1, 'testuser', 'test@example.com')

        response = self.client.post('/user/update',
                                    data={'username': 'testuser'},
                                    content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data.decode('utf-8'))
        self.assertTrue(data.get('success'),
                        f"改为相同用户名应成功，实际: {data}")

    def test_update_username_empty(self):
        """测试用户名为空：应被拒绝"""
        self._login_as(1, 'testuser')

        response = self.client.post('/user/update',
                                    data={'username': ''},
                                    content_type='application/x-www-form-urlencoded')
        data = json.loads(response.data.decode('utf-8'))
        self.assertFalse(data.get('success'), "空用户名应被拒绝")

    def test_update_username_too_short(self):
        """测试用户名过短（少于3字符）：应被拒绝"""
        self._login_as(1, 'testuser')

        response = self.client.post('/user/update',
                                    data={'username': 'ab'},
                                    content_type='application/x-www-form-urlencoded')
        data = json.loads(response.data.decode('utf-8'))
        self.assertFalse(data.get('success'), "过短用户名应被拒绝")

    # ========== 邮箱修改测试 ==========

    def test_update_email_success(self):
        """测试成功修改邮箱：DB和session都应更新"""
        self._login_as(1, 'testuser', 'test@example.com')

        response = self.client.post('/user/update',
                                    data={'email': 'new@example.com'},
                                    content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data.decode('utf-8'))
        self.assertTrue(data.get('success'), f"邮箱修改应成功，实际: {data}")

        # 验证数据库已更新
        with self.app.app_context():
            from app.utils.database import get_db
            conn = get_db()
            c = conn.cursor()
            c.execute('SELECT email FROM users WHERE id = ?', (1,))
            row = c.fetchone()
            self.assertEqual(row['email'], 'new@example.com')

        # 验证 session 已更新
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('email'), 'new@example.com')

    def test_update_email_invalid_format(self):
        """测试无效邮箱格式：应被拒绝"""
        self._login_as(1, 'testuser')

        invalid_emails = ['invalid', 'no-at-sign', '@nouser.com', 'user@', 'user@.com']
        for email in invalid_emails:
            response = self.client.post('/user/update',
                                        data={'email': email},
                                        content_type='application/x-www-form-urlencoded')
            data = json.loads(response.data.decode('utf-8'))
            self.assertFalse(data.get('success'),
                             f"无效邮箱 '{email}' 应被拒绝，实际: {data}")

        # 验证数据库未被修改
        with self.app.app_context():
            from app.utils.database import get_db
            conn = get_db()
            c = conn.cursor()
            c.execute('SELECT email FROM users WHERE id = ?', (1,))
            row = c.fetchone()
            self.assertEqual(row['email'], 'test@example.com',
                             "电子邮件不应修改为无效格式")

    def test_update_email_empty(self):
        """测试邮箱为空：应被拒绝（邮箱不能为空）"""
        self._login_as(1, 'testuser')

        response = self.client.post('/user/update',
                                    data={'email': ''},
                                    content_type='application/x-www-form-urlencoded')
        data = json.loads(response.data.decode('utf-8'))
        self.assertFalse(data.get('success'), "空邮箱应被拒绝")

    # ========== 批量修改测试 ==========

    def test_update_both_fields_success(self):
        """测试同时修改用户名和邮箱：两者都应成功更新"""
        self._login_as(1, 'testuser', 'test@example.com')

        response = self.client.post('/user/update',
                                    data={'username': 'newname',
                                          'email': 'new@example.com'},
                                    content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data.decode('utf-8'))
        self.assertTrue(data.get('success'), f"同时修改应成功，实际: {data}")

        # 验证数据库
        with self.app.app_context():
            from app.utils.database import get_db
            conn = get_db()
            c = conn.cursor()
            c.execute('SELECT username, email FROM users WHERE id = ?', (1,))
            row = c.fetchone()
            self.assertEqual(row['username'], 'newname')
            self.assertEqual(row['email'], 'new@example.com')

        # 验证 session
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('username'), 'newname')
            self.assertEqual(sess.get('email'), 'new@example.com')

    def test_update_both_fields_email_invalid(self):
        """测试同时修改，邮箱无效：整个请求应被拒绝"""
        self._login_as(1, 'testuser')

        response = self.client.post('/user/update',
                                    data={'username': 'newname',
                                          'email': 'bad-email'},
                                    content_type='application/x-www-form-urlencoded')
        data = json.loads(response.data.decode('utf-8'))
        self.assertFalse(data.get('success'),
                         "邮箱无效时整个请求应失败")

        # 验证数据库均未被修改
        with self.app.app_context():
            from app.utils.database import get_db
            conn = get_db()
            c = conn.cursor()
            c.execute('SELECT username, email FROM users WHERE id = ?', (1,))
            row = c.fetchone()
            self.assertEqual(row['username'], 'testuser',
                             "无效请求不应修改用户名")
            self.assertEqual(row['email'], 'test@example.com',
                             "无效请求不应修改邮箱")

    # ========== 管理员测试 ==========

    def test_admin_username_immutable(self):
        """测试管理员（user_id=3, username='admin'）不能修改用户名"""
        self._login_as(3, 'admin', 'admin@example.com', is_admin=True)

        response = self.client.post('/user/update',
                                    data={'username': 'newadmin'},
                                    content_type='application/x-www-form-urlencoded')
        data = json.loads(response.data.decode('utf-8'))
        self.assertFalse(data.get('success'),
                         "管理员不应能修改用户名")

        # 验证数据库未被修改
        with self.app.app_context():
            from app.utils.database import get_db
            conn = get_db()
            c = conn.cursor()
            c.execute('SELECT username FROM users WHERE id = ?', (3,))
            row = c.fetchone()
            self.assertEqual(row['username'], 'admin',
                             "管理员用户名不应被修改")

    def test_admin_can_update_email(self):
        """测试管理员可以修改邮箱"""
        self._login_as(3, 'admin', 'admin@example.com', is_admin=True)

        response = self.client.post('/user/update',
                                    data={'email': 'admin_new@example.com'},
                                    content_type='application/x-www-form-urlencoded')
        data = json.loads(response.data.decode('utf-8'))
        self.assertTrue(data.get('success'),
                        f"管理员应能修改邮箱，实际: {data}")

        # 验证 session 已更新
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('email'), 'admin_new@example.com')


if __name__ == '__main__':
    unittest.main()
