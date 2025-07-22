"""
端口管理原子服务
管理端口分配、释放和状态跟踪
"""

import os
import json
import socket
import fcntl
from typing import Dict, Any, Optional, List
from datetime import datetime


class PortManager:
    """端口管理原子服务"""
    
    def __init__(self, port_range_start: int = 8000, port_range_end: int = 9000):
        self.port_range_start = port_range_start
        self.port_range_end = port_range_end
        self.port_state_file = "/tmp/port_manager_state.json"
        
    def allocate_port(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """分配可用端口"""
        try:
            with self._lock_port_file():
                state = self._load_port_state()
                
                # 查找可用端口
                for port in range(self.port_range_start, self.port_range_end + 1):
                    if self._is_port_available(port) and str(port) not in state["allocated"]:
                        # 分配端口
                        state["allocated"][str(port)] = {
                            "service_name": service_name or f"service_{port}",
                            "allocated_at": datetime.now().isoformat(),
                            "status": "allocated"
                        }
                        
                        self._save_port_state(state)
                        
                        return {
                            "success": True,
                            "port": port,
                            "service_name": service_name or f"service_{port}",
                            "allocated_at": datetime.now().isoformat()
                        }
                
                return {
                    "success": False,
                    "error": "No available ports in range",
                    "port_range": f"{self.port_range_start}-{self.port_range_end}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def release_port(self, port: int) -> Dict[str, Any]:
        """释放端口"""
        try:
            with self._lock_port_file():
                state = self._load_port_state()
                
                port_str = str(port)
                if port_str in state["allocated"]:
                    # 记录释放信息
                    released_info = state["allocated"][port_str].copy()
                    released_info["released_at"] = datetime.now().isoformat()
                    
                    # 从分配状态中移除
                    del state["allocated"][port_str]
                    
                    # 添加到历史记录
                    if "history" not in state:
                        state["history"] = []
                    state["history"].append(released_info)
                    
                    # 只保留最近100条历史记录
                    if len(state["history"]) > 100:
                        state["history"] = state["history"][-100:]
                    
                    self._save_port_state(state)
                    
                    return {
                        "success": True,
                        "port": port,
                        "service_name": released_info.get("service_name"),
                        "released_at": datetime.now().isoformat()
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Port {port} is not allocated",
                        "port": port
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "port": port
            }
    
    def check_port_available(self, port: int) -> Dict[str, Any]:
        """检查端口是否可用"""
        try:
            # 检查端口是否在管理范围内
            if not (self.port_range_start <= port <= self.port_range_end):
                return {
                    "success": True,
                    "port": port,
                    "available": False,
                    "reason": "Port outside managed range",
                    "managed_range": f"{self.port_range_start}-{self.port_range_end}"
                }
            
            # 检查端口是否被系统占用
            system_available = self._is_port_available(port)
            
            # 检查端口是否被我们的服务占用
            state = self._load_port_state()
            allocated_by_us = str(port) in state["allocated"]
            
            available = system_available and not allocated_by_us
            
            result = {
                "success": True,
                "port": port,
                "available": available,
                "system_available": system_available,
                "allocated_by_service": allocated_by_us
            }
            
            if allocated_by_us:
                result["service_info"] = state["allocated"][str(port)]
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "port": port
            }
    
    def get_port_usage(self) -> Dict[str, Any]:
        """获取端口使用情况"""
        try:
            state = self._load_port_state()
            
            allocated_ports = []
            for port_str, info in state["allocated"].items():
                port_info = info.copy()
                port_info["port"] = int(port_str)
                
                # 检查服务是否真的在运行
                if self._is_port_available(int(port_str)):
                    port_info["actual_status"] = "not_running"
                else:
                    port_info["actual_status"] = "running"
                
                allocated_ports.append(port_info)
            
            # 统计信息
            total_range = self.port_range_end - self.port_range_start + 1
            allocated_count = len(allocated_ports)
            available_count = total_range - allocated_count
            
            return {
                "success": True,
                "port_range": f"{self.port_range_start}-{self.port_range_end}",
                "total_ports": total_range,
                "allocated_count": allocated_count,
                "available_count": available_count,
                "allocated_ports": allocated_ports,
                "history_count": len(state.get("history", [])),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def cleanup_stale_allocations(self) -> Dict[str, Any]:
        """清理无效的端口分配（端口已释放但状态未更新）"""
        try:
            with self._lock_port_file():
                state = self._load_port_state()
                cleaned_ports = []
                
                for port_str in list(state["allocated"].keys()):
                    port = int(port_str)
                    if self._is_port_available(port):
                        # 端口实际未被使用，清理分配状态
                        cleaned_info = state["allocated"][port_str].copy()
                        cleaned_info["cleaned_at"] = datetime.now().isoformat()
                        cleaned_info["reason"] = "port_not_in_use"
                        
                        del state["allocated"][port_str]
                        cleaned_ports.append(cleaned_info)
                
                self._save_port_state(state)
                
                return {
                    "success": True,
                    "cleaned_count": len(cleaned_ports),
                    "cleaned_ports": cleaned_ports,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _is_port_available(self, port: int) -> bool:
        """检查端口是否在系统级别可用"""
        try:
            # 尝试绑定端口
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('localhost', port))
                return True
        except OSError:
            return False
    
    def _load_port_state(self) -> Dict[str, Any]:
        """加载端口状态"""
        if not os.path.exists(self.port_state_file):
            return {
                "allocated": {},
                "history": [],
                "created_at": datetime.now().isoformat()
            }
        
        try:
            with open(self.port_state_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # 文件损坏，返回默认状态
            return {
                "allocated": {},
                "history": [],
                "created_at": datetime.now().isoformat()
            }
    
    def _save_port_state(self, state: Dict[str, Any]) -> None:
        """保存端口状态"""
        state["last_updated"] = datetime.now().isoformat()
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self.port_state_file), exist_ok=True)
        
        with open(self.port_state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def _lock_port_file(self):
        """文件锁上下文管理器"""
        class FileLock:
            def __init__(self, file_path):
                self.file_path = file_path + ".lock"
                self.lock_file = None
            
            def __enter__(self):
                self.lock_file = open(self.file_path, 'w')
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX)
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                if self.lock_file:
                    fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                    self.lock_file.close()
                try:
                    os.remove(self.file_path)
                except OSError:
                    pass
        
        return FileLock(self.port_state_file)