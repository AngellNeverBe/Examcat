"""
examcat - 工具函数包
"""

# 导入子模块
from . import database
from . import auth
from . import questions
from . import helpers

# 从database模块重新导出常用函数
from .database import (
    get_db,
    init_db,
    migrate_database,
    get_available_banks,
    get_current_bank,
    set_current_bank,
    load_questions_to_db,
    load_all_banks,
    get_questions_by_bank,
    get_current_question_id,
    get_next_question_id,
    get_bank_progress,
    extract_qid_number
)

# 从auth模块重新导出常用函数
from .auth import (
    login_required,
    is_logged_in,
    get_user_id
)

# 从questions模块重新导出常用函数
from .questions import (
    fetch_question,
    random_question_id,
    fetch_random_question_ids,
    is_favorite
)

# 从helpers模块重新导出常用函数
from .helpers import (
    format_time,
    paginate,
    validate_csv_file,
    generate_unique_id
)

# 定义公开的API接口
__all__ = [
    # 模块
    'database',
    'auth', 
    'questions',
    'helpers',
    
    # 数据库函数
    'get_db',
    'init_db',
    'migrate_database',
    'get_available_banks',
    'get_current_bank',
    'set_current_bank',
    'load_questions_to_db',
    'load_all_banks',
    'get_questions_by_bank',
    'get_current_question_id',
    'get_next_question_id',
    'get_bank_progress',
    'extract_qid_number',
    
    # 认证函数
    'login_required',
    'is_logged_in',
    'get_user_id',
    
    # 题目函数
    'fetch_question',
    'random_question_id',
    'fetch_random_question_ids',
    'is_favorite',
    
    # 辅助函数
    'format_time',
    'paginate',
    'validate_csv_file',
    'generate_unique_id'
]

# 版本信息
__version__ = '1.0'
__author__ = 'paracat (https://github.com/AngellNeverBe)'
__description__ = 'examcat 工具函数包'

# 包初始化时的逻辑
def _init_package():
    """初始化工具包（可选）"""
    import os
    import sys
    
    # 可以在这里添加包初始化逻辑
    # 例如：检查依赖、配置日志等
    
    # 打印初始化信息（仅开发环境）
    if os.getenv('FLASK_ENV') == 'development':
        print(f"[INFO] 初始化 {__name__} 包 v{__version__}")

# 自动执行初始化
_init_package()

# 提供包的元信息
def get_package_info():
    """获取工具包信息"""
    return {
        'name': __name__,
        'version': __version__,
        'author': __author__,
        'description': __description__,
        'modules': ['database', 'auth', 'questions', 'helpers']
    }

# 方便的函数别名（可选）
# 为常用函数提供简短别名
db = get_db
require_login = login_required
fetch_q = fetch_question
rand_qid = random_question_id

# 兼容性导入（确保旧代码可以工作）
# 如果之前有直接导入utils的函数，可以通过这些变量提供向后兼容
compatibility_exports = {
    'get_db': get_db,
    'login_required': login_required,
    'fetch_question': fetch_question
}