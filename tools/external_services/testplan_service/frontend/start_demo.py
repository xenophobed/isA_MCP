#!/usr/bin/env python3
"""
3GPP测试系统前端演示启动脚本
启动本地HTTP服务器来运行前端应用
"""

import http.server
import socketserver
import webbrowser
import os
import sys
from pathlib import Path

def main():
    # 获取当前脚本所在目录
    frontend_dir = Path(__file__).parent
    
    # 切换到前端目录
    os.chdir(frontend_dir)
    
    # 设置端口
    PORT = 8000
    
    print("🚀 Starting 3GPP Test Management Platform...")
    print(f"📁 Working Directory: {frontend_dir}")
    print(f"🌐 Server Port: {PORT}")
    
    # Create HTTP server
    Handler = http.server.SimpleHTTPRequestHandler
    
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"✅ Server started: http://localhost:{PORT}")
            print("📱 Demo Account:")
            print("   Username: demo")
            print("   Password: demo123")
            print("\n🔧 Professional Features:")
            print("   • Enterprise Authentication System")
            print("   • Real-time Test Dashboard")
            print("   • Advanced Test Plan Management")
            print("   • Drag & Drop File Upload")
            print("   • Multi-format Export (XLSX/CSV/PDF)")
            print("   • Responsive Design")
            print("   • Professional UI/UX")
            print("\n⌨️  Keyboard Shortcuts:")
            print("   • Ctrl+K: Global Search")
            print("   • Ctrl+R: Refresh Data")
            print("   • Esc: Close Modals")
            print("   • F1: Help Information")
            print("\n🛑 Press Ctrl+C to stop server")
            
            # Auto-open browser
            try:
                webbrowser.open(f"http://localhost:{PORT}")
                print("🌐 Browser opened automatically")
            except Exception as e:
                print(f"⚠️  Unable to open browser automatically: {e}")
                print(f"📖 Please visit manually: http://localhost:{PORT}")
            
            # Start server
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
        sys.exit(0)
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"❌ Port {PORT} is already in use, please try another port")
            print("💡 You can check port usage with:")
            print(f"   lsof -i :{PORT}")
        else:
            print(f"❌ Failed to start server: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unknown error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
