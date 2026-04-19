"""
examcat - 客户端cookie辅助函数
"""
import os
import logging
from typing import Dict
from flask import Response

def set_cookies_from_dict(resp: Response, cookie_dict: Dict[str, str]) -> Response:
    """
    将cookie字典设置到响应对象中
    
    Args:
        resp: Flask响应对象
        cookie_dict: cookie字典 {key: value}
        
    Returns:
        resp: 设置好cookie的响应对象
    """
    if not cookie_dict:
        return resp
    
    for key, value in cookie_dict.items():
        # 设置cookie，有效期30天，路径为根路径
        resp.set_cookie(
            key=key,
            value=value,
            max_age=30*24*60*60,  # 30天
            path='/',
            httponly=False,  # 允许前端JavaScript访问
            samesite='Lax'
        )
    
    cookie_logger.debug(f"设置cookie: {list(cookie_dict.keys())}")
    return resp

def delete_cookie(resp: Response, key: str) -> Response:
    """
    删除指定的Cookie
    
    Args:
        resp: Flask响应对象
        key: 要删除的Cookie键名
        
    Returns:
        resp: 更新后的响应对象
    """
    resp.delete_cookie(key=key, path='/')
    cookie_logger.debug(f"删除cookie: {key}")
    return resp

def delete_cookies_from_list(resp: Response, keys: list) -> Response:
    """
    批量删除Cookie
    
    Args:
        resp: Flask响应对象
        keys: 要删除的Cookie键名列表
        
    Returns:
        resp: 更新后的响应对象
    """
    for key in keys:
        resp.delete_cookie(key=key, path='/')
    
    if keys:
        cookie_logger.debug(f"批量删除cookie: {keys}")
    
    return resp

def update_current_seq_qid_cookie(resp: Response, current_seq_qid: int, next_qid: int = None) -> Response:
    """
    更新当前题目Cookie
    
    Args:
        resp: Flask响应对象
        current_seq_qid: 当前题目ID（用于删除旧Cookie）
        next_qid: 下一题题目ID（用于设置新Cookie）
        
    Returns:
        resp: 更新后的响应对象
    """
    # 删除旧的当前题目Cookie
    delete_cookie(resp, 'current_seq_qid')
    cookie_logger.debug(f"删除旧的current_seq_qid cookie: {current_seq_qid}")
    
    # 如果有下一题，设置新的Cookie
    if next_qid:
        resp.set_cookie(
            key='current_seq_qid',
            value=str(next_qid),
            max_age=30*24*60*60,  # 30天
            path='/',
            httponly=False,
            samesite='Lax'
        )
        cookie_logger.debug(f"设置新的current_seq_qid cookie: {next_qid}")
    
    return resp

# ================= Cookie日志配置 =================
def setup_cookie_logger():
    """设置Cookie专用日志记录器"""
    # 创建日志目录（如果不存在）
    log_dir = '/var/log/examcat'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # 创建Cookie专用日志记录器
    cookie_logger = logging.getLogger('examcat.cookie')
    cookie_logger.setLevel(logging.INFO)  # 记录INFO及以上级别的日志
    
    # 避免重复添加处理器
    if not cookie_logger.handlers:
        # 创建文件处理器
        log_file = os.path.join(log_dir, 'cookie.log')
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # 添加到记录器
        cookie_logger.addHandler(file_handler)
    
    return cookie_logger

# 创建全局Cookie日志记录器
cookie_logger = setup_cookie_logger()