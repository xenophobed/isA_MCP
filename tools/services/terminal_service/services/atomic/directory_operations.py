"""
目录操作原子服务
最基础的目录系统操作，不依赖任何其他服务
"""

import os
import shutil
from typing import Dict, Any, List
from datetime import datetime


class DirectoryOperations:
    """目录操作原子服务"""
    
    @staticmethod
    def create_directory(dir_path: str, recursive: bool = True) -> Dict[str, Any]:
        """创建目录 - 最基础的原子操作"""
        try:
            if recursive:
                os.makedirs(dir_path, exist_ok=True)
            else:
                os.mkdir(dir_path)
            
            return {
                "success": True,
                "directory_path": dir_path,
                "recursive": recursive,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "directory_path": dir_path
            }
    
    @staticmethod
    def delete_directory(dir_path: str, recursive: bool = False) -> Dict[str, Any]:
        """删除目录"""
        try:
            if not os.path.exists(dir_path):
                return {
                    "success": False,
                    "error": "Directory does not exist",
                    "directory_path": dir_path
                }
            
            if recursive:
                shutil.rmtree(dir_path)
            else:
                os.rmdir(dir_path)  # 只删除空目录
            
            return {
                "success": True,
                "directory_path": dir_path,
                "action": "deleted",
                "recursive": recursive,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "directory_path": dir_path
            }
    
    @staticmethod
    def list_directory(dir_path: str, include_hidden: bool = False) -> Dict[str, Any]:
        """列出目录内容"""
        try:
            if not os.path.exists(dir_path):
                return {
                    "success": False,
                    "error": "Directory does not exist",
                    "directory_path": dir_path
                }
            
            items = []
            for item in os.listdir(dir_path):
                if not include_hidden and item.startswith('.'):
                    continue
                
                item_path = os.path.join(dir_path, item)
                stat = os.stat(item_path)
                
                items.append({
                    "name": item,
                    "path": item_path,
                    "is_directory": os.path.isdir(item_path),
                    "is_file": os.path.isfile(item_path),
                    "size": stat.st_size,
                    "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "permissions": oct(stat.st_mode)[-3:]
                })
            
            return {
                "success": True,
                "directory_path": dir_path,
                "items": items,
                "count": len(items),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "directory_path": dir_path
            }
    
    @staticmethod
    def directory_exists(dir_path: str) -> Dict[str, Any]:
        """检查目录是否存在"""
        return {
            "success": True,
            "directory_path": dir_path,
            "exists": os.path.exists(dir_path),
            "is_directory": os.path.isdir(dir_path) if os.path.exists(dir_path) else False,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def create_directory_structure(base_path: str, structure: List[str]) -> Dict[str, Any]:
        """批量创建目录结构"""
        try:
            created_dirs = []
            failed_dirs = []
            
            for dir_name in structure:
                full_path = os.path.join(base_path, dir_name)
                result = DirectoryOperations.create_directory(full_path)
                
                if result["success"]:
                    created_dirs.append(full_path)
                else:
                    failed_dirs.append({
                        "path": full_path,
                        "error": result["error"]
                    })
            
            return {
                "success": len(failed_dirs) == 0,
                "base_path": base_path,
                "created_directories": created_dirs,
                "failed_directories": failed_dirs,
                "total_requested": len(structure),
                "total_created": len(created_dirs),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "base_path": base_path
            } 