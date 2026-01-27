#!/usr/bin/env python3
"""
知识图谱构建器 - 前端测试服务器

使用此脚本启动前端测试页面，避免 CORS 问题
"""

import http.server
import socketserver
import webbrowser
import os
import sys
from pathlib import Path

# 配置
PORT = 8000
FRONTEND_DIR = Path(__file__).parent

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """自定义 HTTP 请求处理器"""

    def end_headers(self):
        # 添加 CORS 头，允许跨域请求
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()

    def do_OPTIONS(self):
        # 处理 OPTIONS 预检请求
        self.send_response(200)
        self.end_headers()

def start_server():
    """启动 HTTP 服务器"""

    # 切换到前端目录
    os.chdir(FRONTEND_DIR)

    # 创建服务器
    handler = MyHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"""
╔═══════════════════════════════════════════════════════╗
║   🧠 知识图谱构建器 - API 测试平台                    ║
╠═══════════════════════════════════════════════════════╣
║                                                       ║
║   ✅ 服务器已启动！                                   ║
║                                                       ║
║   📍 测试页面地址:                                    ║
║   http://localhost:{PORT}/test.html                    ║
║                                                       ║
║   💡 提示:                                            ║
║   1. 确保后端服务已启动 (python backend/app.py)      ║
║   2. 后端地址: http://localhost:7860                  ║
║                                                       ║
║   ⏹️  按 Ctrl+C 停止服务器                           ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
        """)

        # 自动打开浏览器
        try:
            webbrowser.open(f'http://localhost:{PORT}/test.html')
        except Exception as e:
            print(f"⚠️  无法自动打开浏览器: {e}")
            print(f"👆 请手动访问: http://localhost:{PORT}/test.html")

        try:
            # 运行服务器
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n✋ 服务器已停止")

if __name__ == "__main__":
    start_server()
