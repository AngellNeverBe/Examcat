# examcat/gunicorn_conf.py

import os
import sys
from pathlib import Path

# 1. 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 2. 加载 .env 文件
try:
    from dotenv import load_dotenv
    # 加载项目根目录的 .env 文件
    env_path = project_root / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        print(f"已加载 .env 文件: {env_path}")
    else:
        print(f"ERR: 未找到 .env 文件: {env_path}")
except ImportError:
    print("ERR: 未安装 python-dotenv，请运行: pip install python-dotenv")
except Exception as e:
    print(f"ERR: 加载 .env 文件失败: {e}")

# 3. 尝试访问已加载的环境变量
required_vars = ['FLASK_ENV', 'SECRET_KEY']
for var in required_vars:
    if not os.environ.get(var):
        print(f"ERR: 环境变量 {var} 未设置")

# Gunicorn 生产配置
bind = "localhost:32220"  # 绑定端口，与您的入口点一致
workers = 9              # 工作进程数，建议设为 2*CPU核心数+1
worker_class = "sync"    # 工作模式
timeout = 120            # 请求超时时间（秒）
keepalive = 60           # 保持连接时间
max_requests = 1000      # 最大请求数后重启worker
max_requests_jitter = 50 # 随机抖动，防止同时重启

# 日志配置
accesslog = "/var/log/examcat/access.log"
errorlog = "/var/log/examcat/error.log"
loglevel = "info"

# 进程名称
proc_name = "examcat"

# 环境变量 - .env 中的变量会自动加载
raw_env = ["FLASK_ENV=production"]