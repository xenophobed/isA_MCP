"""
文件操作原子服务
最基础的文件系统操作，不依赖任何其他服务
"""

import os
import tempfile
from typing import Dict, Any, Optional
from datetime import datetime


class FileOperations:
    """文件操作原子服务"""
    
    @staticmethod
    def create_file(file_path: str, content: str, executable: bool = False) -> Dict[str, Any]:
        """创建文件 - 最基础的原子操作"""
        try:
            # 确保目录存在
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 设置执行权限
            if executable:
                os.chmod(file_path, 0o755)
            
            return {
                "success": True,
                "file_path": file_path,
                "size": len(content),
                "executable": executable,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }
    
    @staticmethod
    def read_file(file_path: str) -> Dict[str, Any]:
        """读取文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "success": True,
                "file_path": file_path,
                "content": content,
                "size": len(content),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }
    
    @staticmethod
    def delete_file(file_path: str) -> Dict[str, Any]:
        """删除文件"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return {
                    "success": True,
                    "file_path": file_path,
                    "action": "deleted",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": "File does not exist",
                    "file_path": file_path
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }
    
    @staticmethod
    def file_exists(file_path: str) -> Dict[str, Any]:
        """检查文件是否存在"""
        return {
            "success": True,
            "file_path": file_path,
            "exists": os.path.exists(file_path),
            "is_file": os.path.isfile(file_path) if os.path.exists(file_path) else False,
            "timestamp": datetime.now().isoformat()
        } 