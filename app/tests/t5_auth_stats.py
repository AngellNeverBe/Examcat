#!/usr/bin/env python3
"""
examcat - auth.py 统计函数测试
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app
from app.utils.auth import (
    fetch_user_question_stats,
    fetch_user_question_stats_by_category,
    get_user_overall_stats,
    get_user_type_stats,
    get_user_category_stats
)


class AuthStatsTestCase(unittest.TestCase):
    """auth.py 统计函数测试用例"""

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

        # 初始化测试数据库并插入测试数据
        with self.app.app_context():
            from app.utils.database import get_db, init_db
            init_db()

            # 插入测试数据
            conn = get_db()
            c = conn.cursor()

            # 清空所有表，避免唯一约束冲突（注意外键顺序）
            c.execute('DELETE FROM history')
            c.execute('DELETE FROM questions')
            c.execute('DELETE FROM banks')
            c.execute('DELETE FROM users')

            # 插入用户
            c.execute('INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                     ('testuser', 'test@example.com', 'hash'))

            # 插入题库
            c.execute('INSERT INTO banks (bankname, type, category, total_count) VALUES (?, ?, ?, ?)',
                     ('测试题库1', '选择题', '大一', 10))
            c.execute('INSERT INTO banks (bankname, type, category, total_count) VALUES (?, ?, ?, ?)',
                     ('测试题库2', '填空题', '大二', 5))

            # 插入题目
            # 题库1的题目
            for i in range(1, 11):
                c.execute('''
                    INSERT INTO questions (bank_id, stem, answer, type, category, "order")
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (1, f'题目{i}', f'答案{i}', '选择题', '大一', i))

            # 题库2的题目
            for i in range(1, 6):
                c.execute('''
                    INSERT INTO questions (bank_id, stem, answer, type, category, "order")
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (2, f'题目{i}', f'答案{i}', '填空题', '大二', i))

            # 插入答题记录（history表）
            # 先清空历史记录，避免唯一约束冲突
            c.execute('DELETE FROM history')

            # 用户1在题库1的答题记录
            # 题目1：正确1次，complete=1, correct=1
            c.execute('''
                INSERT INTO history (user_id, question_id, bank_id, complete, last_answer, correct, correct_count, wrong_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (1, 1, 1, 1, 'A', 1, 1, 0))

            # 题目2：正确2次，wrong1次，complete=1, correct=1（最后一次正确）
            c.execute('''
                INSERT INTO history (user_id, question_id, bank_id, complete, last_answer, correct, correct_count, wrong_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (1, 2, 1, 1, 'B', 1, 2, 1))

            # 题目3：错误1次，complete=1, correct=0
            c.execute('''
                INSERT INTO history (user_id, question_id, bank_id, complete, last_answer, correct, correct_count, wrong_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (1, 3, 1, 1, 'C', 0, 0, 1))

            # 题目4：错误2次，correct1次，complete=1, correct=0（最后一次错误）
            c.execute('''
                INSERT INTO history (user_id, question_id, bank_id, complete, last_answer, correct, correct_count, wrong_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (1, 4, 1, 1, 'D', 0, 1, 2))

            # 题目5：未完成，complete=0
            c.execute('''
                INSERT INTO history (user_id, question_id, bank_id, complete, last_answer, correct, correct_count, wrong_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (1, 5, 1, 0, 'E', 0, 0, 0))

            # 用户1在题库2的答题记录
            # 题目6（题库2的题目1）：正确1次
            c.execute('''
                INSERT INTO history (user_id, question_id, bank_id, complete, last_answer, correct, correct_count, wrong_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (1, 11, 2, 1, 'A', 1, 1, 0))

            # 题目7（题库2的题目2）：错误1次
            c.execute('''
                INSERT INTO history (user_id, question_id, bank_id, complete, last_answer, correct, correct_count, wrong_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (1, 12, 2, 1, 'B', 0, 0, 1))

            conn.commit()

    def tearDown(self):
        """在每个测试之后运行，清理资源"""
        # 弹出应用上下文
        self.app_context.pop()

    def test_fetch_user_question_stats_correct_counts(self):
        """测试 fetch_user_question_stats 正确统计数目和次数"""
        # 题库1的统计
        stats = fetch_user_question_stats(1, 1)

        # 验证数目统计
        # answered: complete=1的记录数 = 4 (题目1,2,3,4)
        self.assertEqual(stats['answered'], 4, "已答题目数应为4")

        # correct: correct=1的记录数 = 2 (题目1,2)
        # 注意：题目4虽然correct_count>0但correct=0（最后一次错误）
        self.assertEqual(stats['correct'], 2, "正确题目数应为2")

        # wrong: correct=0的记录数 = 2 (题目3,4)
        self.assertEqual(stats['wrong'], 2, "错误题目数应为2")

        # correct_count: SUM(correct_count) = 1+2+0+1 = 4
        self.assertEqual(stats['correct_count'], 4, "总正确次数应为4")

        # wrong_count: SUM(wrong_count) = 0+1+1+2 = 4
        self.assertEqual(stats['wrong_count'], 4, "总错误次数应为4")

        # total: 题库总题目数 = 10
        self.assertEqual(stats['total'], 10, "题库总题目数应为10")

        # 验证百分比计算（基于题目数量）
        # correct_percentage = correct/answered = 2/4 = 50%
        self.assertAlmostEqual(stats['correct_percentage'], 50.0, places=2,
                              msg="正确题目百分比应为50%")

        # wrong_percentage = wrong/answered = 2/4 = 50%
        self.assertAlmostEqual(stats['wrong_percentage'], 50.0, places=2,
                              msg="错误题目百分比应为50%")

        # correct_total_percentage = correct/total = 2/10 = 20%
        self.assertAlmostEqual(stats['correct_total_percentage'], 20.0, places=2,
                              msg="正确题目占总题目百分比应为20%")

        # wrong_total_percentage = wrong/total = 2/10 = 20%
        self.assertAlmostEqual(stats['wrong_total_percentage'], 20.0, places=2,
                              msg="错误题目占总题目百分比应为20%")

        # unanswered = total - answered = 10 - 4 = 6
        self.assertEqual(stats['unanswered'], 6, "未答题目数应为6")

        # unanswered_percentage = 6/10 = 60%
        self.assertAlmostEqual(stats['unanswered_percentage'], 60.0, places=2,
                              msg="未答题目百分比应为60%")

    def test_fetch_user_question_stats_by_category(self):
        """测试 fetch_user_question_stats_by_category 按分类统计"""
        # 用户1在题库1中'大一'分类的统计
        stats = fetch_user_question_stats_by_category(1, 1, '大一')

        # 验证数目统计（应该与全题库统计相同，因为所有题目都是'大一'分类）
        self.assertEqual(stats['answered'], 4, "分类已答题目数应为4")
        self.assertEqual(stats['correct'], 2, "分类正确题目数应为2")
        self.assertEqual(stats['wrong'], 2, "分类错误题目数应为2")
        self.assertEqual(stats['correct_count'], 4, "分类总正确次数应为4")
        self.assertEqual(stats['wrong_count'], 4, "分类总错误次数应为4")
        self.assertEqual(stats['total'], 10, "分类总题目数应为10")

    def test_get_user_overall_stats(self):
        """测试 get_user_overall_stats 总体统计"""
        stats = get_user_overall_stats(1)

        # 验证统计字段
        # total: 所有题库complete=1的记录数 = 6 (题库1的4个 + 题库2的2个)
        self.assertEqual(stats['total'], 6, "总已答题目数应为6")

        # correct: correct=1的记录数 = 3 (题库1:题目1,2; 题库2:题目6)
        self.assertEqual(stats['correct'], 3, "总正确题目数应为3")

        # wrong: correct=0的记录数 = 3 (题库1:题目3,4; 题库2:题目7)
        self.assertEqual(stats['wrong'], 3, "总错误题目数应为3")

        # correct_count: 所有题库正确次数总和 = 4+1 = 5
        self.assertEqual(stats['correct_count'], 5, "总正确次数应为5")

        # wrong_count: 所有题库错误次数总和 = 4+1 = 5
        self.assertEqual(stats['wrong_count'], 5, "总错误次数应为5")

        # overall_accuracy: correct/total = 3/6 = 50%
        self.assertAlmostEqual(stats['overall_accuracy'], 50.0, places=2,
                              msg="总体正确率应为50%")

    def test_get_user_type_stats(self):
        """测试 get_user_type_stats 按题型统计"""
        type_stats = get_user_type_stats(1)

        # 应该有两个题型：选择题（题库1）和填空题（题库2）
        self.assertEqual(len(type_stats), 2, "应有两个题型的统计")

        # 查找选择题统计
        choice_stats = None
        fill_stats = None
        for stat in type_stats:
            if stat['type'] == '选择题':
                choice_stats = stat
            elif stat['type'] == '填空题':
                fill_stats = stat

        # 验证选择题统计
        self.assertIsNotNone(choice_stats, "应包含选择题统计")
        self.assertEqual(choice_stats['total'], 4, "选择题总已答题目数应为4")
        self.assertEqual(choice_stats['correct'], 2, "选择题正确题目数应为2")
        self.assertEqual(choice_stats['wrong'], 2, "选择题错误题目数应为2")
        self.assertEqual(choice_stats['correct_count'], 4, "选择题总正确次数应为4")
        self.assertEqual(choice_stats['wrong_count'], 4, "选择题总错误次数应为4")
        # accuracy = correct/total = 2/4 = 50%
        self.assertAlmostEqual(choice_stats['accuracy'], 50.0, places=2,
                              msg="选择题正确率应为50%")

        # 验证填空题统计
        self.assertIsNotNone(fill_stats, "应包含填空题统计")
        self.assertEqual(fill_stats['total'], 2, "填空题总已答题目数应为2")
        self.assertEqual(fill_stats['correct'], 1, "填空题正确题目数应为1")
        self.assertEqual(fill_stats['wrong'], 1, "填空题错误题目数应为1")
        self.assertEqual(fill_stats['correct_count'], 1, "填空题总正确次数应为1")
        self.assertEqual(fill_stats['wrong_count'], 1, "填空题总错误次数应为1")
        # accuracy = correct/total = 1/2 = 50%
        self.assertAlmostEqual(fill_stats['accuracy'], 50.0, places=2,
                              msg="填空题正确率应为50%")

    def test_get_user_category_stats(self):
        """测试 get_user_category_stats 按分类统计"""
        category_stats = get_user_category_stats(1)

        # 应该有两个分类：大一（题库1）和大二（题库2）
        self.assertEqual(len(category_stats), 2, "应有两个分类的统计")

        # 查找大一和大二统计
        大一_stats = None
        大二_stats = None
        for stat in category_stats:
            if stat['category'] == '大一':
                大一_stats = stat
            elif stat['category'] == '大二':
                大二_stats = stat

        # 验证大一统计（题库1）
        self.assertIsNotNone(大一_stats, "应包含大一分类统计")
        self.assertEqual(大一_stats['total'], 4, "大一总已答题目数应为4")
        self.assertEqual(大一_stats['correct'], 2, "大一正确题目数应为2")
        self.assertEqual(大一_stats['wrong'], 2, "大一错误题目数应为2")
        self.assertEqual(大一_stats['correct_count'], 4, "大一总正确次数应为4")
        self.assertEqual(大一_stats['wrong_count'], 4, "大一总错误次数应为4")
        # accuracy = correct/total = 2/4 = 50%
        self.assertAlmostEqual(大一_stats['accuracy'], 50.0, places=2,
                              msg="大一正确率应为50%")

        # 验证大二统计（题库2）
        self.assertIsNotNone(大二_stats, "应包含大二分类统计")
        self.assertEqual(大二_stats['total'], 2, "大二总已答题目数应为2")
        self.assertEqual(大二_stats['correct'], 1, "大二正确题目数应为1")
        self.assertEqual(大二_stats['wrong'], 1, "大二错误题目数应为1")
        self.assertEqual(大二_stats['correct_count'], 1, "大二总正确次数应为1")
        self.assertEqual(大二_stats['wrong_count'], 1, "大二总错误次数应为1")
        # accuracy = correct/total = 1/2 = 50%
        self.assertAlmostEqual(大二_stats['accuracy'], 50.0, places=2,
                              msg="大二正确率应为50%")


if __name__ == '__main__':
    unittest.main()