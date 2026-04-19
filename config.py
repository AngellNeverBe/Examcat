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
    CARD_INFO = 'Examcat 正在准备一个大更新！不保证3.22以后的数据安全！预计：<br><font color="red">1.重构项目代码，增加浏览速度，优化UI设计</font><br>2.修复不能返回上一题的问题<br>3.修复被医综伤到的心 T_T'
    
    """ Artalk """
    ARTALK_ENABLED = True                             # 是否启用 Artalk
    ARTALK_SERVER = 'https://artalk.paraisland.top'   # Artalk 后端地址
    ARTALK_SITE_NAME = 'Examcat'                      # 站点名称
    ARTALK_LOCALE = 'zh-CN'                           # 语言设置

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