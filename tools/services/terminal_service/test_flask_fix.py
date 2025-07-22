#!/usr/bin/env python3
"""
测试Flask代码修复
"""

import sys
import os
import tempfile
import subprocess
import time
import requests

current_dir = os.path.dirname(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, project_root)

def create_simple_blog_app(app_name, port=8002):
    """创建简单的Flask应用"""
    
    app_code = f'''#!/usr/bin/env python3
from flask import Flask, jsonify, render_template_string
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'test_key_123'

@app.route('/')
def home():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head><title>{{{{ app_name }}}}</title></head>
    <body>
        <h1>🚀 {{{{ app_name }}</h1>
        <p>✅ Flask应用已成功启动！</p>
        <p>🕒 当前时间: {{{{ timestamp }}}}</p>
    </body>
    </html>
    """, app_name="{app_name}", timestamp=datetime.now())

@app.route('/health')
def health():
    return jsonify({{"status": "ok", "service": "{app_name}"}})

if __name__ == '__main__':
    print(f"🚀 启动 {app_name} 应用")
    print(f"🌐 访问地址: http://localhost:{port}")
    app.run(host='0.0.0.0', port={port}, debug=False)
'''
    
    return app_code

def test_flask_app():
    """测试Flask应用"""
    
    print("🧪 测试Flask应用修复")
    print("=" * 50)
    
    # 创建临时项目
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 临时目录: {temp_dir}")
        
        # 生成应用代码
        app_code = create_simple_blog_app("测试博客", 8002)
        app_file = os.path.join(temp_dir, "app.py")
        
        with open(app_file, 'w', encoding='utf-8') as f:
            f.write(app_code)
        
        print(f"📄 应用代码: {len(app_code)} 字符")
        
        # 启动Flask应用
        print("🚀 启动Flask应用...")
        process = subprocess.Popen(
            ['python', app_file],
            cwd=temp_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        print(f"✅ 进程PID: {process.pid}")
        
        # 等待启动
        time.sleep(3)
        
        # 检查进程状态
        if process.poll() is not None:
            print(f"❌ 进程已退出，返回码: {process.returncode}")
            stdout, stderr = process.communicate()
            if stdout:
                print(f"📝 输出: {stdout}")
            if stderr:
                print(f"🚨 错误: {stderr}")
            return False
        
        print("✅ 进程运行中")
        
        # 测试HTTP访问
        try:
            response = requests.get("http://localhost:8002/", timeout=5)
            print(f"📊 HTTP状态码: {response.status_code}")
            
            if response.status_code == 500:
                # 获取错误日志
                stdout, stderr = process.communicate(timeout=2)
                if stderr:
                    print(f"🚨 Flask错误日志: {stderr}")
            
            if response.status_code == 200:
                print("✅ HTTP访问成功")
                print(f"📄 响应长度: {len(response.text)} 字符")
                
                # 测试健康检查
                health_response = requests.get("http://localhost:8002/health", timeout=5)
                if health_response.status_code == 200:
                    print("✅ 健康检查成功")
                    print(f"📊 健康状态: {health_response.json()}")
                else:
                    print(f"⚠️ 健康检查失败: {health_response.status_code}")
                
            else:
                print(f"❌ HTTP访问失败: {response.status_code}")
                
        except Exception as e:
            print(f"❌ HTTP请求异常: {e}")
        
        finally:
            # 清理进程
            print("🧹 清理进程...")
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                process.kill()
        
        print("✅ 测试完成")

if __name__ == '__main__':
    test_flask_app()