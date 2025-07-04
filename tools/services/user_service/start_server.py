#!/usr/bin/env python3
"""
User Service API Server Launcher

启动用户管理服务的 FastAPI 服务器
提供开发和生产环境的不同配置
"""

import argparse
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.services.user_service.api_server import start_server


def main():
    """主函数，解析命令行参数并启动服务器"""
    parser = argparse.ArgumentParser(
        description="启动用户管理服务 API 服务器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 开发模式（热重载）
  python start_server.py --dev
  
  # 生产模式
  python start_server.py --host 0.0.0.0 --port 8000
  
  # 自定义端口
  python start_server.py --port 8080
        """
    )
    
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="服务器监听地址 (默认: 127.0.0.1)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="服务器监听端口 (默认: 8000)"
    )
    
    parser.add_argument(
        "--dev",
        action="store_true",
        help="开发模式 (启用热重载和调试)"
    )
    
    parser.add_argument(
        "--reload",
        action="store_true",
        help="启用热重载 (仅开发时使用)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error"],
        default="info",
        help="日志级别 (默认: info)"
    )
    
    args = parser.parse_args()
    
    # 开发模式配置
    if args.dev:
        host = "127.0.0.1"
        reload = True
        log_level = "debug"
        print("🚀 启动开发模式服务器...")
    else:
        host = args.host
        reload = args.reload
        log_level = args.log_level
        print("🏭 启动生产模式服务器...")
    
    # 显示启动信息
    print(f"📡 服务器地址: http://{host}:{args.port}")
    print(f"📚 API 文档: http://{host}:{args.port}/docs")
    print(f"🔄 热重载: {'启用' if reload else '禁用'}")
    print(f"📝 日志级别: {log_level}")
    print("-" * 50)
    
    try:
        # 启动服务器
        start_server(
            host=host,
            port=args.port,
            reload=reload
        )
    except KeyboardInterrupt:
        print("\n⏹️  服务器已停止")
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 