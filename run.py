#!/usr/bin/env python3
"""
examcat - 应用入口点
"""
import os

from dotenv import load_dotenv  # 新增
# 在创建应用之前加载 .env 文件
load_dotenv()  # 默认加载当前目录的 .env 文件
# 或指定路径：load_dotenv('/path/to/.env')
from app import create_app
# 创建应用实例
app = create_app()
if __name__ == '__main__':
    # 删除根目录的questions.csv文件提示
    if os.path.exists('questions.csv'):
        print("注意：检测到根目录的questions.csv文件，建议将其移动到questions-bank/文件夹中")
        print("当前系统将优先使用questions-bank/文件夹中的题库")
    
    # 运行应用
    app.run(host="localhost", debug=True, port=32220)