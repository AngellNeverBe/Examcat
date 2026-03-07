"""
examcat - 配置文件
"""
import os
from datetime import timedelta

class Config:
    """基础配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(24))
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    DATABASE_PATH = os.environ.get('DATABASE_PATH', 'database.db')
    QUESTIONS_BANK_DIR = os.environ.get('QUESTIONS_BANK_DIR', './app/questions-bank')

    """个性化配置"""
    TITLE = 'Examcat'
    CARD_INFO = 'Examcat 1.0 版本正式启动！<br>这是一个多题库刷题软件，完善了原先的ExamMaster多个功能，并重构了项目结构。<br>欢迎您提出宝贵的意见！这里是俺的 <a href="https://blog.paraisland.top" class="footer-link" target="_blank" rel="noopener noreferrer">blog</a> 和 <a href="https://github.com/AngellNeverBe" class="footer-link" target="_blank" rel="noopener noreferrer">GitHub</a>，欢迎参观！'
    
    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    TESTING = False
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        # 生产环境特定的初始化
        # 确保SECRET_KEY来自环境变量
        if not os.environ.get('SECRET_KEY'):
            raise ValueError("SECRET_KEY must be set in production environment")

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}