"""
examcat - 蓝图注册模块
"""

from .auth import auth_bp
from .main import main_bp
from .questions import questions_bp
from .banks import banks_bp
from .exams import exams_bp
from .statistics import statistics_bp
from .favorites import favorites_bp
from .browse import browse_bp

# 可选：如果创建了api蓝图
# from .api import api_bp

__all__ = [
    'auth_bp', 'main_bp', 'questions_bp', 'banks_bp',
    'exams_bp', 'statistics_bp', 'favorites_bp', 'browse_bp'
]