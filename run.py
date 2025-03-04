#!/usr/bin/env python
"""
run map app
"""

import os
import sys
import webbrowser
from time import sleep
import subprocess
import platform
import argparse

def check_dependencies():
    """check_dependencies"""
    try:
        import flask
        import xarray
        import numpy
        import netCDF4
        return True
    except ImportError as e:
        print(f"lack of dependency: {e}")
        print("pip install -r requirements.txt")
        return False

def check_data_file():
    """check data file"""
    if not os.path.exists("concatenated_MVBS.nc"):
        print("Error: cannot find concatenated_MVBS.nc")
        return False
    return True

def create_folder_structure():
    """create_folder_structure"""
    folders = ['static', 'static/css', 'static/js']
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
            print(f"create folder: {folder}")

def open_browser(url, delay=1.5):
    def _open_browser():
        sleep(delay)
        webbrowser.open(url)
    
    import threading
    threading.Thread(target=_open_browser).start()

def main():

    parser = argparse.ArgumentParser(description="open map app")
    parser.add_argument("--no-browser", action="store_true", help="No browser.")
    parser.add_argument("--port", type=int, default=5000, help="port")
    args = parser.parse_args()
    
    # check dependencies
    if not check_dependencies() or not check_data_file():
        return 1
    
    # create folder
    create_folder_structure()
    
    # check files
    required_files = {
        'app.py': 'backend',
        'index.html': 'index',
        'static/css/styles.css': 'CSS',
        'static/js/app.js': 'JavaScript'
    }
    
    missing_files = []
    for file_path, description in required_files.items():
        if not os.path.exists(file_path):
            missing_files.append(f"{file_path} ({description})")
    
    if missing_files:
        print("Error: lack of file:")
        for file in missing_files:
            print(f"  - {file}")
        return 1
    
    # 启动应用
    port = args.port
    url = f"http://localhost:{port}"
    
    print(f"run app at port {port}...")
    print(f"visit: {url}")
    
    if not args.no_browser:
        print("Open browser...")
        open_browser(url)
    
    # set environment
    os.environ["FLASK_APP"] = "app.py"
    os.environ["FLASK_ENV"] = "development"
    
    # run Flask
    from app import app
    app.run(debug=True, host='0.0.0.0', port=port)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())