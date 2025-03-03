#!/usr/bin/env python
"""
一键启动声学数据地图应用
"""

import os
import sys
import webbrowser
from time import sleep
import subprocess
import platform
import argparse

def check_dependencies():
    """检查依赖是否已安装"""
    try:
        import flask
        import xarray
        import numpy
        import netCDF4
        return True
    except ImportError as e:
        print(f"缺少依赖项: {e}")
        print("请先安装必要的依赖: pip install -r requirements.txt")
        return False

def check_data_file():
    """检查数据文件是否存在"""
    if not os.path.exists("concatenated_MVBS.nc"):
        print("错误: 找不到 concatenated_MVBS.nc 文件")
        print("请将数据文件放在当前目录并重试")
        return False
    return True

def create_folder_structure():
    """创建必要的文件夹结构"""
    folders = ['static', 'static/css', 'static/js']
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
            print(f"创建文件夹: {folder}")

def open_browser(url, delay=1.5):
    """在延迟后打开浏览器"""
    def _open_browser():
        sleep(delay)
        webbrowser.open(url)
    
    import threading
    threading.Thread(target=_open_browser).start()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="启动声学数据地图应用")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--port", type=int, default=5000, help="指定端口号")
    args = parser.parse_args()
    
    # 检查依赖和数据文件
    if not check_dependencies() or not check_data_file():
        return 1
    
    # 创建文件夹结构
    create_folder_structure()
    
    # 检查文件是否存在
    required_files = {
        'app.py': '后端应用',
        'data_processor.py': '数据处理模块',
        'index.html': '主页面',
        'static/css/styles.css': 'CSS样式表',
        'static/js/app.js': '前端JavaScript'
    }
    
    missing_files = []
    for file_path, description in required_files.items():
        if not os.path.exists(file_path):
            missing_files.append(f"{file_path} ({description})")
    
    if missing_files:
        print("错误: 缺少以下文件:")
        for file in missing_files:
            print(f"  - {file}")
        print("请确保所有必要文件已正确放置")
        return 1
    
    # 启动应用
    port = args.port
    url = f"http://localhost:{port}"
    
    print(f"启动声学数据地图应用在端口 {port}...")
    print(f"应用将可在以下地址访问: {url}")
    
    if not args.no_browser:
        print("正在打开浏览器...")
        open_browser(url)
    
    # 设置环境变量并启动Flask
    os.environ["FLASK_APP"] = "app.py"
    os.environ["FLASK_ENV"] = "development"
    
    # 启动Flask应用
    from app import app
    app.run(debug=True, host='0.0.0.0', port=port)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())