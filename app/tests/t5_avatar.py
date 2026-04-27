"""
t5_avatar.py - 头像 URL 生成功能测试
"""
import unittest
from app.utils.helpers import get_avatar_url


class AvatarUrlTestCase(unittest.TestCase):
    """get_avatar_url() 函数单元测试"""

    def test_known_email_produces_correct_hash(self):
        """验证已知邮箱生成正确的 WeAvatar URL"""
        url = get_avatar_url("test@example.com")
        expected = "https://weavatar.com/avatar/973dfe463ec85785f5f95af5ba3906eedb2d931c24e69824a89ea65dba4e813b?sha256=1&d=mp&s=240"
        self.assertEqual(url, expected)

    def test_empty_email(self):
        """验证空邮箱返回空字符串"""
        self.assertEqual(get_avatar_url(""), "")
        self.assertEqual(get_avatar_url(None), "")

    def test_whitespace_trimmed(self):
        """验证邮箱前后空格被去除"""
        url1 = get_avatar_url("test@example.com")
        url2 = get_avatar_url("  test@example.com  ")
        self.assertEqual(url1, url2)

    def test_case_insensitive(self):
        """验证邮箱大小写不影响哈希结果"""
        url1 = get_avatar_url("Test@Example.com")
        url2 = get_avatar_url("test@example.com")
        self.assertEqual(url1, url2)


if __name__ == '__main__':
    unittest.main()
