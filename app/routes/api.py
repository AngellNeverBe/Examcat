"""
examcat - API路由蓝图（RESTful API）
"""
import os
import requests
from flask import Blueprint, jsonify
from ..utils.auth import login_required

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/exams', methods=['GET'])
@login_required
def get_exams():
    """
    从 WebDAV 获取考试列表 JSON，失败时降级返回模拟数据。
    """
    # 从环境变量读取配置（安全）
    webdav_url = os.environ.get('WEBDAV_EXAMS_URL', 'http://webdav.paraisland.top:2627/zju/exams.json')
    webdav_user = os.environ.get('WEBDAV_USER')
    webdav_pass = os.environ.get('WEBDAV_PASS')

    # 尝试从 WebDAV 获取真实数据
    try:
        auth = (webdav_user, webdav_pass) if webdav_user and webdav_pass else None
        resp = requests.get(webdav_url, auth=auth, timeout=5)
        resp.raise_for_status()  # 如果状态码不是 2xx 则抛出异常
        exams = resp.json()
        if isinstance(exams, list):
            return jsonify(exams)
    except Exception as e:
        # 记录错误（可选）
        # app.logger.warning(f"从 WebDAV 获取考试数据失败: {e}")
        pass

    # 降级：返回模拟数据
    import datetime
    current_year = datetime.datetime.now().year
    mock_exams = [
        {"course": "消化与内分泌系统Ⅱ", "date": f"{current_year}-04-26"},
        {"course": "心血管、呼吸、血液与泌尿系统Ⅱ", "date": f"{current_year}-05-10"}
    ]
    return jsonify(mock_exams)