#!/usr/bin/env python3
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return '<h1>Hello QuickApp!</h1><p>Flask is working!</p>'

@app.route('/health')
def health():
    return {'status': 'ok'}

if __name__ == '__main__':
    print("🚀 启动简单Flask应用")
    print("🌐 访问地址: http://localhost:8003")
    app.run(host='0.0.0.0', port=8003, debug=False)