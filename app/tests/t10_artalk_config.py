#!/usr/bin/env python3
"""
examcat - Artalk评论系统配置测试
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


class ArtalkConfigTestCase(unittest.TestCase):
    """Artalk评论系统配置测试用例"""
    
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
    
    def test_artalk_config_exists(self):
        """测试Artalk配置在config.py中是否正确设置"""
        # 检查配置类中的Artalk相关设置
        self.assertIn('ARTALK_ENABLED', self.app.config, "缺少ARTALK_ENABLED配置")
        self.assertIn('ARTALK_SERVER', self.app.config, "缺少ARTALK_SERVER配置")
        self.assertIn('ARTALK_SITE_NAME', self.app.config, "缺少ARTALK_SITE_NAME配置")
        self.assertIn('ARTALK_LOCALE', self.app.config, "缺少ARTALK_LOCALE配置")
        
        # 检查配置值是否有效
        self.assertIsInstance(self.app.config['ARTALK_ENABLED'], bool, "ARTALK_ENABLED应为布尔值")
        self.assertIsInstance(self.app.config['ARTALK_SERVER'], str, "ARTALK_SERVER应为字符串")
        self.assertIsInstance(self.app.config['ARTALK_SITE_NAME'], str, "ARTALK_SITE_NAME应为字符串")
        self.assertIsInstance(self.app.config['ARTALK_LOCALE'], str, "ARTALK_LOCALE应为字符串")
        
        print(f"ARTALK配置检查通过: enabled={self.app.config['ARTALK_ENABLED']}, "
              f"server={self.app.config['ARTALK_SERVER']}, "
              f"site={self.app.config['ARTALK_SITE_NAME']}, "
              f"locale={self.app.config['ARTALK_LOCALE']}")
    
    def test_base_template_includes_artalk_config(self):
        """测试base.html模板是否正确包含Artalk配置"""
        # 直接检查模板文件
        template_path = os.path.join(os.path.dirname(__file__), '../templates/base.html')
        
        # 检查模板文件是否存在
        self.assertTrue(os.path.exists(template_path), f"base.html模板文件不存在: {template_path}")
        
        # 读取模板内容
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # 检查Artalk.js脚本引入
        self.assertIn('cdnjs.cloudflare.com/ajax/libs/artalk/2.9.1/Artalk.js', template_content,
                      "base.html模板未引入Artalk.js脚本")
        
        # 检查Artalk配置脚本
        self.assertIn('window.ARTALK_CONFIG', template_content,
                      "base.html模板未设置window.ARTALK_CONFIG")
        
        # 检查Artalk管理器脚本（注意模板中使用url_for）
        self.assertIn("{{ url_for('static', filename='js/artalk-manager.js') }}", template_content,
                      "base.html模板未引入artalk-manager.js")
        
        # 检查配置变量是否正确传递
        self.assertIn('{{ config.ARTALK_SERVER }}', template_content,
                      "base.html模板未包含ARTALK_SERVER配置变量")
        self.assertIn('{{ config.ARTALK_SITE_NAME }}', template_content,
                      "base.html模板未包含ARTALK_SITE_NAME配置变量")
        self.assertIn('{{ config.ARTALK_LOCALE }}', template_content,
                      "base.html模板未包含ARTALK_LOCALE配置变量")
        
        print("base.html模板Artalk配置检查通过")
    
    def test_question_template_contains_artalk_container(self):
        """测试题目模板是否包含Artalk评论区容器"""
        # 直接检查模板文件（注意文件在_partial目录下）
        template_path = os.path.join(os.path.dirname(__file__), '../templates/_partial/_question_content.html')
        
        # 检查模板文件是否存在
        self.assertTrue(os.path.exists(template_path), f"题目模板文件不存在: {template_path}")
        
        # 读取模板内容
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # 检查是否包含Artalk容器
        self.assertIn('id="artalk-section"', template_content,
                      "题目模板缺少artalk-section容器")
        self.assertIn('id="Comments"', template_content,
                      "题目模板缺少Comments容器")
        self.assertIn('data-page-key', template_content,
                      "题目模板缺少data-page-key属性")
        self.assertIn('artalk-comment-count', template_content,
                      "题目模板缺少评论计数元素")
        
        # 检查是否已更新（不再使用ES模块导入）
        self.assertNotIn('import Artalk from', template_content,
                         "题目模板仍然包含旧的ES模块导入方式")
        
        print("题目模板Artalk容器检查通过")
    
    def test_artalk_manager_js_exists(self):
        """测试artalk-manager.js文件是否存在且语法正确"""
        js_path = os.path.join(os.path.dirname(__file__), '../static/js/artalk-manager.js')
        
        # 检查文件是否存在
        self.assertTrue(os.path.exists(js_path), "artalk-manager.js文件不存在")
        
        # 读取文件内容
        with open(js_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # 检查关键函数和类定义
        self.assertIn('const ArtalkManager', js_content, "缺少ArtalkManager定义")
        self.assertIn('function init', js_content, "缺少init函数")
        self.assertIn('function showComments', js_content, "缺少showComments函数")
        self.assertIn('function hideComments', js_content, "缺少hideComments函数")
        self.assertIn('window.ArtalkManager = ArtalkManager', js_content, "未导出到全局对象")
        
        # 检查事件监听
        self.assertIn("ajax:page:updated", js_content, "未监听ajax:page:updated事件")
        
        print("artalk-manager.js文件检查通过")
    
    def test_question_js_integration(self):
        """测试question.js是否集成Artalk功能"""
        js_path = os.path.join(os.path.dirname(__file__), '../static/js/question.js')
        
        # 检查文件是否存在
        self.assertTrue(os.path.exists(js_path), "question.js文件不存在")
        
        # 读取文件内容
        with open(js_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # 检查showCommentsSection函数是否更新
        self.assertIn('showCommentsSection', js_content, "缺少showCommentsSection函数")
        
        # 检查是否包含ArtalkManager调用
        self.assertIn('window.ArtalkManager', js_content, "question.js未调用ArtalkManager")
        self.assertIn('showComments', js_content, "question.js未调用showComments函数")
        
        print("question.js集成检查通过")
    
    def test_ajax_navigator_includes_artalk_manager(self):
        """测试ajax_navigator.js是否包含artalk-manager.js作为全局资源"""
        js_path = os.path.join(os.path.dirname(__file__), '../static/js/ajax_navigator.js')
        
        # 检查文件是否存在
        self.assertTrue(os.path.exists(js_path), "ajax_navigator.js文件不存在")
        
        # 读取文件内容
        with open(js_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # 检查是否将artalk-manager.js列为全局脚本资源
        self.assertIn('/static/js/artalk-manager.js', js_content,
                      "ajax_navigator.js未将artalk-manager.js列为全局资源")
        
        print("ajax_navigator.js集成检查通过")


if __name__ == '__main__':
    unittest.main()