"""
examcat - 应用工厂模块
"""
import os
from flask import Flask, render_template
from functools import lru_cache

def create_app(config_name=None):
    """应用工厂函数，用于创建Flask应用实例"""
    app = Flask(__name__)
    
    # 加载配置
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'development')
    
    # 加载配置类
    if config_name == 'production':
        app.config.from_object('config.ProductionConfig')
    else:
        app.config.from_object('config.DevelopmentConfig')
    
    # 初始化扩展
    from .extentions import init_extensions
    init_extensions(app)
    
    # 注册蓝图
    register_blueprints(app)
    
    # 注册错误处理器
    register_error_handlers(app)
    
    # 初始化数据库
    with app.app_context():
        from .utils.database import init_db, load_all_banks
        init_db()
        load_all_banks()    
    @lru_cache(maxsize=1)
    def get_app_config():
        """缓存配置获取，提高性能"""
        return {
            'app_title': app.config.get('TITLE', 'Examcat'),
            'card_info': app.config.get('CARD_INFO', 'Examcat 正式上线')
        }
    
    @app.context_processor
    def inject_config_variables():
        """将配置变量注入所有模板"""
        return {
            'config': app.config,  # 注入整个config对象
            'app_title': app.config.get('TITLE', 'Examcat'),
            'card_info': app.config.get('CARD_INFO', 'Examcat 正式上线')
        }
    
    return app

def register_blueprints(app):
    """注册所有蓝图"""
    from .routes.auth import auth_bp
    from .routes.main import main_bp
    from .routes.questions import questions_bp
    from .routes.banks import banks_bp
    from .routes.exams import exams_bp
    from .routes.statistics import statistics_bp
    from .routes.favorites import favorites_bp
    from .routes.browse import browse_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(questions_bp)
    app.register_blueprint(banks_bp)
    app.register_blueprint(exams_bp)
    app.register_blueprint(statistics_bp)
    app.register_blueprint(favorites_bp)
    app.register_blueprint(browse_bp)


def register_error_handlers(app):
    """注册错误处理器"""
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('error.html', error_code=404, error_message="页面不存在"), 404
    
    @app.errorhandler(500)
    def server_error(e):
        return render_template('error.html', error_code=500, error_message="服务器内部错误"), 500