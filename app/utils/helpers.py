"""
examcat - 通用辅助函数模块
"""
import os
import json
import time
import random
import string
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from functools import wraps
from werkzeug.utils import secure_filename

# ============================================================================
# 时间处理函数
# ============================================================================

def format_time(timestamp: Optional[str] = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化时间戳或当前时间为可读字符串。
    
    Args:
        timestamp: 时间戳字符串（可选），如果为None则使用当前时间
        fmt: 时间格式字符串，默认为"%Y-%m-%d %H:%M:%S"
    
    Returns:
        格式化后的时间字符串
    """
    if timestamp:
        try:
            # 尝试解析多种时间格式
            for time_fmt in ["%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
                try:
                    dt = datetime.strptime(timestamp, time_fmt)
                    return dt.strftime(fmt)
                except ValueError:
                    continue
            # 如果所有格式都失败，返回原始字符串
            return timestamp
        except Exception:
            return timestamp
    else:
        return datetime.now().strftime(fmt)

def format_duration(seconds: int) -> str:
    """
    将秒数格式化为可读的时间字符串。
    
    Args:
        seconds: 秒数
    
    Returns:
        格式化后的时间字符串，如"2天 03:45:30"
    """
    if seconds <= 0:
        return "00:00:00"
    
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if days > 0:
        return f"{days}天 {hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def time_since(dt: datetime) -> str:
    """
    计算给定时间距离现在的时间差，返回人性化描述。
    
    Args:
        dt: 要计算的时间
    
    Returns:
        人性化时间描述，如"刚刚", "5分钟前", "2小时前"
    """
    now = datetime.now()
    diff = now - dt
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years}年前"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months}个月前"
    elif diff.days > 0:
        return f"{diff.days}天前"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours}小时前"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes}分钟前"
    else:
        return "刚刚"

def is_expired(timestamp: str, expiry_seconds: int) -> bool:
    """
    检查给定的时间戳是否已过期。
    
    Args:
        timestamp: 时间戳字符串
        expiry_seconds: 过期秒数
    
    Returns:
        如果已过期返回True，否则返回False
    """
    try:
        dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
        expiry_time = dt + timedelta(seconds=expiry_seconds)
        return datetime.now() > expiry_time
    except Exception:
        return True

# ============================================================================
# 分页处理函数
# ============================================================================

def paginate(data_list: List, page: int, per_page: int) -> Dict[str, Any]:
    """
    对列表数据进行分页处理。
    
    Args:
        data_list: 数据列表
        page: 当前页码（从1开始）
        per_page: 每页数据量
    
    Returns:
        包含分页信息的字典：
        {
            'items': 当前页的数据,
            'page': 当前页码,
            'per_page': 每页数量,
            'total': 总数据量,
            'pages': 总页数,
            'has_prev': 是否有上一页,
            'has_next': 是否有下一页
        }
    """
    if page < 1:
        page = 1
    
    total = len(data_list)
    pages = (total + per_page - 1) // per_page
    
    # 计算起始和结束索引
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    # 防止索引越界
    if start_idx >= total:
        items = []
    else:
        items = data_list[start_idx:end_idx]
    
    return {
        'items': items,
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': pages,
        'has_prev': page > 1,
        'has_next': page < pages
    }

def get_pagination_info(page: int, per_page: int, total: int) -> Dict[str, Any]:
    """
    根据分页参数生成分页信息。
    
    Args:
        page: 当前页码
        per_page: 每页数量
        total: 总数据量
    
    Returns:
        分页信息字典
    """
    pages = (total + per_page - 1) // per_page if total > 0 else 1
    
    # 确保页码在有效范围内
    if page < 1:
        page = 1
    elif page > pages and pages > 0:
        page = pages
    
    return {
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': pages,
        'has_prev': page > 1,
        'has_next': page < pages,
        'prev_page': page - 1 if page > 1 else None,
        'next_page': page + 1 if page < pages else None
    }

# ============================================================================
# 文件处理函数
# ============================================================================

def validate_csv_file(filepath: str) -> Tuple[bool, str]:
    """
    验证CSV文件是否有效。
    
    Args:
        filepath: CSV文件路径
    
    Returns:
        (是否有效, 错误信息)
    """
    try:
        if not os.path.exists(filepath):
            return False, "文件不存在"
        
        # 检查文件大小
        file_size = os.path.getsize(filepath)
        if file_size == 0:
            return False, "文件为空"
        
        if file_size > 10 * 1024 * 1024:  # 10MB限制
            return False, "文件大小超过10MB限制"
        
        # 检查文件扩展名
        if not filepath.lower().endswith('.csv'):
            return False, "文件必须是CSV格式"
        
        # 尝试读取文件头（只读取第一行）
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            first_line = f.readline().strip()
            if not first_line:
                return False, "CSV文件头部为空"
        
        return True, "文件有效"
    except UnicodeDecodeError:
        return False, "文件编码错误，请使用UTF-8编码"
    except Exception as e:
        return False, f"文件验证失败: {str(e)}"

def get_file_extension(filename: str) -> str:
    """
    获取文件扩展名（小写）。
    
    Args:
        filename: 文件名
    
    Returns:
        文件扩展名（不带点）
    """
    return os.path.splitext(filename)[1].lower().lstrip('.')

def is_allowed_file(filename: str, allowed_extensions: set) -> bool:
    """
    检查文件扩展名是否在允许的列表中。
    
    Args:
        filename: 文件名
        allowed_extensions: 允许的扩展名集合，如{'csv', 'txt'}
    
    Returns:
        如果允许返回True，否则返回False
    """
    return '.' in filename and get_file_extension(filename) in allowed_extensions

def secure_upload_filename(filename: str) -> str:
    """
    安全处理上传的文件名。
    
    Args:
        filename: 原始文件名
    
    Returns:
        安全的文件名
    """
    # 使用werkzeug的secure_filename，并添加时间戳避免重名
    base_name = secure_filename(os.path.splitext(filename)[0])
    ext = get_file_extension(filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_{timestamp}.{ext}"

def get_file_size_readable(size_bytes: int) -> str:
    """
    将文件大小转换为可读的字符串。
    
    Args:
        size_bytes: 字节数
    
    Returns:
        可读的文件大小字符串，如"1.5 MB"
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

# ============================================================================
# 字符串处理函数
# ============================================================================

def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断字符串到指定长度，并在末尾添加后缀。
    
    Args:
        text: 原始文本
        max_length: 最大长度（包含后缀长度）
        suffix: 截断后添加的后缀
    
    Returns:
        截断后的字符串
    """
    if len(text) <= max_length:
        return text
    
    # 确保后缀不会使字符串超过最大长度
    actual_max = max_length - len(suffix)
    if actual_max <= 0:
        return suffix[:max_length]
    
    return text[:actual_max] + suffix

def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    安全地解析JSON字符串，如果解析失败返回默认值。
    
    Args:
        json_str: JSON字符串
        default: 解析失败时返回的默认值
    
    Returns:
        解析后的JSON对象或默认值
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default

def generate_random_string(length: int = 8, include_digits: bool = True, 
                          include_letters: bool = True) -> str:
    """
    生成随机字符串。
    
    Args:
        length: 字符串长度
        include_digits: 是否包含数字
        include_letters: 是否包含字母
    
    Returns:
        随机字符串
    """
    chars = ""
    if include_digits:
        chars += string.digits
    if include_letters:
        chars += string.ascii_letters
    
    if not chars:
        chars = string.ascii_letters + string.digits
    
    return ''.join(random.choice(chars) for _ in range(length))

def generate_unique_id(prefix: str = "") -> str:
    """
    生成唯一的ID字符串。
    
    Args:
        prefix: ID前缀
    
    Returns:
        唯一ID字符串
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_str = generate_random_string(6)
    return f"{prefix}{timestamp}_{random_str}"

def md5_hash(text: str) -> str:
    """
    计算字符串的MD5哈希值。
    
    Args:
        text: 要哈希的文本
    
    Returns:
        MD5哈希值（32位十六进制字符串）
    """
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def get_avatar_url(email):
    """
    根据邮箱地址生成 WeAvatar 头像 URL（SHA-256 哈希）。
    遵循 Gravatar 协议：邮箱去除空白并转为小写后取 SHA-256。

    Args:
        email: 邮箱地址

    Returns:
        WeAvatar 头像 URL，若邮箱为空则返回空字符串
    """
    if not email:
        return ''
    email_clean = email.strip().lower()
    email_hash = hashlib.sha256(email_clean.encode('utf-8')).hexdigest()
    return f'https://weavatar.com/avatar/{email_hash}?sha256=1&d=mp&s=240'


# ============================================================================
# 验证函数
# ============================================================================

def validate_username(username: str) -> Tuple[bool, str]:
    """
    验证用户名是否有效。
    
    Args:
        username: 用户名
    
    Returns:
        (是否有效, 错误信息)
    """
    if not username:
        return False, "用户名不能为空"
    
    if len(username) < 3:
        return False, "用户名至少需要3个字符"
    
    if len(username) > 50:
        return False, "用户名不能超过50个字符"
    
    # 只允许字母、数字、下划线、中文
    import re
    if not re.match(r'^[\w\u4e00-\u9fa5]+$', username):
        return False, "用户名只能包含字母、数字、下划线和中文"
    
    return True, "用户名有效"

def validate_password(password: str) -> Tuple[bool, str]:
    """
    验证密码是否有效。
    
    Args:
        password: 密码
    
    Returns:
        (是否有效, 错误信息)
    """
    if not password:
        return False, "密码不能为空"
    
    if len(password) < 6:
        return False, "密码至少需要6个字符"
    
    if len(password) > 100:
        return False, "密码不能超过100个字符"
    
    return True, "密码有效"

def validate_email(email: str) -> Tuple[bool, str]:
    """
    验证邮箱地址是否有效。
    
    Args:
        email: 邮箱地址
    
    Returns:
        (是否有效, 错误信息)
    """
    if not email:
        return False, "邮箱地址不能为空"
    
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        return False, "邮箱地址格式无效"
    
    return True, "邮箱地址有效"

# ============================================================================
# 安全相关函数
# ============================================================================

def sanitize_input(input_str: str, max_length: int = 500) -> str:
    """
    清理用户输入，防止XSS攻击和SQL注入。
    
    Args:
        input_str: 用户输入字符串
        max_length: 最大允许长度
    
    Returns:
        清理后的字符串
    """
    if not input_str:
        return ""
    
    # 截断到最大长度
    if len(input_str) > max_length:
        input_str = input_str[:max_length]
    
    # 移除危险的HTML标签
    import re
    dangerous_tags = re.compile(r'<script.*?>.*?</script>|<.*?javascript:.*?>', re.IGNORECASE)
    input_str = dangerous_tags.sub('', input_str)
    
    # 转义HTML特殊字符
    input_str = input_str.replace('&', '&amp;')
    input_str = input_str.replace('<', '&lt;')
    input_str = input_str.replace('>', '&gt;')
    input_str = input_str.replace('"', '&quot;')
    input_str = input_str.replace("'", '&#x27;')
    
    return input_str

def check_password_strength(password: str) -> Tuple[int, str]:
    """
    检查密码强度。
    
    Args:
        password: 密码
    
    Returns:
        (强度等级0-4, 强度描述)
    """
    if not password:
        return 0, "无密码"
    
    score = 0
    feedback = []
    
    # 长度检查
    if len(password) >= 8:
        score += 1
    else:
        feedback.append("密码太短（至少8个字符）")
    
    # 包含数字
    if any(char.isdigit() for char in password):
        score += 1
    else:
        feedback.append("密码应包含数字")
    
    # 包含小写字母
    if any(char.islower() for char in password):
        score += 1
    else:
        feedback.append("密码应包含小写字母")
    
    # 包含大写字母
    if any(char.isupper() for char in password):
        score += 1
    else:
        feedback.append("密码应包含大写字母")
    
    # 包含特殊字符
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if any(char in special_chars for char in password):
        score += 1
    else:
        feedback.append("密码应包含特殊字符")
    
    # 确定强度等级
    if score == 5:
        return 4, "非常强"
    elif score >= 4:
        return 3, "强"
    elif score >= 3:
        return 2, "中等"
    elif score >= 2:
        return 1, "弱"
    else:
        return 0, "非常弱"
    
    # 返回反馈信息（如果有）
    if feedback:
        return score, "; ".join(feedback)
    
    return score, "密码强度未知"

# ============================================================================
# 数据转换函数
# ============================================================================

def convert_to_int(value, default: int = 0) -> int:
    """
    安全地将值转换为整数。
    
    Args:
        value: 要转换的值
        default: 转换失败时的默认值
    
    Returns:
        整数值
    """
    try:
        if value is None:
            return default
        return int(value)
    except (ValueError, TypeError):
        return default

def convert_to_float(value, default: float = 0.0) -> float:
    """
    安全地将值转换为浮点数。
    
    Args:
        value: 要转换的值
        default: 转换失败时的默认值
    
    Returns:
        浮点数值
    """
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default

def convert_to_bool(value, default: bool = False) -> bool:
    """
    安全地将值转换为布尔值。
    
    Args:
        value: 要转换的值
        default: 转换失败时的默认值
    
    Returns:
        布尔值
    """
    if value is None:
        return default
    
    if isinstance(value, bool):
        return value
    
    if isinstance(value, (int, float)):
        return value != 0
    
    if isinstance(value, str):
        value_lower = value.lower()
        if value_lower in ('true', 'yes', '1', 'on', 't'):
            return True
        elif value_lower in ('false', 'no', '0', 'off', 'f'):
            return False
    
    return default

# ============================================================================
# 装饰器函数
# ============================================================================

def admin_required(f):
    """
    装饰器：要求管理员权限。
    注意：此函数需要结合具体的用户权限系统实现。
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # TODO: 实现管理员权限检查
        # 这里只是一个示例，实际使用时需要根据具体权限系统实现
        from flask import abort
        # if not current_user.is_admin:
        #     abort(403)
        return f(*args, **kwargs)
    return decorated_function

def cache_result(ttl: int = 300):
    """
    缓存函数结果的装饰器。
    
    Args:
        ttl: 缓存有效期（秒）
    """
    cache_dict = {}
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # 检查缓存是否有效
            if key in cache_dict:
                result, timestamp = cache_dict[key]
                if time.time() - timestamp < ttl:
                    return result
            
            # 调用原始函数
            result = func(*args, **kwargs)
            
            # 缓存结果
            cache_dict[key] = (result, time.time())
            
            return result
        return wrapper
    return decorator

def retry_on_exception(max_retries: int = 3, delay: float = 1.0, 
                       exceptions: tuple = (Exception,)):
    """
    在异常时重试的装饰器。
    
    Args:
        max_retries: 最大重试次数
        delay: 重试延迟（秒）
        exceptions: 需要重试的异常类型
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(delay * (2 ** attempt))  # 指数退避
                    else:
                        raise last_exception
            
            raise last_exception  # 永远不会执行到这里，但为了完整性保留
        return wrapper
    return decorator

# ============================================================================
# 统计和计算函数
# ============================================================================

def calculate_percentage(part: int, total: int) -> float:
    """
    计算百分比。
    
    Args:
        part: 部分值
        total: 总值
    
    Returns:
        百分比（0-100）
    """
    if total == 0:
        return 0.0
    return (part / total) * 100

def calculate_average(values: List[float]) -> float:
    """
    计算平均值。
    
    Args:
        values: 数值列表
    
    Returns:
        平均值
    """
    if not values:
        return 0.0
    return sum(values) / len(values)

def calculate_progress(current: int, total: int) -> Dict[str, Any]:
    """
    计算进度信息。
    
    Args:
        current: 当前进度
        total: 总进度
    
    Returns:
        包含进度信息的字典
    """
    if total == 0:
        percentage = 0.0
    else:
        percentage = (current / total) * 100
    
    return {
        'current': current,
        'total': total,
        'percentage': round(percentage, 2),
        'remaining': total - current,
        'is_complete': current >= total
    }

# ============================================================================
# 环境检测函数
# ============================================================================

def is_development() -> bool:
    """
    检查是否处于开发环境。
    
    Returns:
        如果是开发环境返回True，否则返回False
    """
    env = os.getenv('FLASK_ENV', 'development')
    return env.lower() == 'development'

def is_production() -> bool:
    """
    检查是否处于生产环境。
    
    Returns:
        如果是生产环境返回True，否则返回False
    """
    env = os.getenv('FLASK_ENV', 'development')
    return env.lower() == 'production'

def get_app_version() -> str:
    """
    获取应用程序版本。
    
    Returns:
        版本字符串
    """
    version_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'VERSION')
    
    if os.path.exists(version_file):
        with open(version_file, 'r') as f:
            return f.read().strip()
    
    return "1.0.0"

# ============================================================================
# 调试和日志函数
# ============================================================================

def debug_print(*args, **kwargs):
    """
    只在开发环境下打印调试信息。
    """
    if is_development():
        print("[DEBUG]", *args, **kwargs)

def log_execution_time(func):
    """
    记录函数执行时间的装饰器。
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        execution_time = end_time - start_time
        debug_print(f"{func.__name__} 执行时间: {execution_time:.4f} 秒")
        
        return result
    return wrapper

# ============================================================================
# 模块初始化
# ============================================================================

# def init_helpers():
    """
    初始化辅助函数模块。
    """
    debug_print("初始化辅助函数模块")
    # 这里可以添加模块初始化逻辑
    
# 自动初始化
# init_helpers()