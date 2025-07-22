"""
服务管理原子服务
管理服务的启动、停止、状态监控
"""

import os
import json
import signal
import subprocess
import psutil
import time
from typing import Dict, Any, Optional, List
from datetime import datetime


class ServiceManager:
    """服务管理原子服务"""
    
    def __init__(self):
        self.services_state_file = "/tmp/service_manager_state.json"
        
    def start_service(
        self, 
        service_name: str, 
        command: str, 
        port: Optional[int] = None,
        working_dir: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """启动服务"""
        try:
            # 检查服务是否已存在
            state = self._load_services_state()
            if service_name in state["services"]:
                existing_service = state["services"][service_name]
                if self._is_process_running(existing_service.get("pid")):
                    return {
                        "success": False,
                        "error": f"Service {service_name} is already running",
                        "service_name": service_name,
                        "existing_pid": existing_service.get("pid")
                    }
                else:
                    # 清理无效的服务记录
                    del state["services"][service_name]
            
            # 准备环境变量
            process_env = os.environ.copy()
            if env_vars:
                process_env.update(env_vars)
            if port:
                process_env["PORT"] = str(port)
            
            # 启动进程
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=working_dir,
                env=process_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # 创建新的进程组
            )
            
            # 等待一小段时间确保进程启动
            time.sleep(1)
            
            # 检查进程是否成功启动
            if process.poll() is not None:
                # 进程已经退出
                stdout, stderr = process.communicate()
                return {
                    "success": False,
                    "error": "Service failed to start",
                    "service_name": service_name,
                    "return_code": process.returncode,
                    "stdout": stdout.decode() if stdout else "",
                    "stderr": stderr.decode() if stderr else ""
                }
            
            # 记录服务信息
            service_info = {
                "service_name": service_name,
                "pid": process.pid,
                "command": command,
                "port": port,
                "working_dir": working_dir,
                "env_vars": env_vars,
                "started_at": datetime.now().isoformat(),
                "status": "running"
            }
            
            state["services"][service_name] = service_info
            self._save_services_state(state)
            
            return {
                "success": True,
                "service_name": service_name,
                "pid": process.pid,
                "port": port,
                "started_at": service_info["started_at"],
                "command": command
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "service_name": service_name
            }
    
    def stop_service(self, service_name: str, force: bool = False) -> Dict[str, Any]:
        """停止服务"""
        try:
            state = self._load_services_state()
            
            if service_name not in state["services"]:
                return {
                    "success": False,
                    "error": f"Service {service_name} not found",
                    "service_name": service_name
                }
            
            service_info = state["services"][service_name]
            pid = service_info.get("pid")
            
            if not self._is_process_running(pid):
                # 进程已经不存在，清理记录
                del state["services"][service_name]
                self._save_services_state(state)
                
                return {
                    "success": True,
                    "service_name": service_name,
                    "message": "Service was not running, cleaned up record",
                    "was_running": False
                }
            
            # 停止进程
            stopped = self._stop_process(pid, force)
            
            if stopped:
                # 记录停止信息
                service_info["stopped_at"] = datetime.now().isoformat()
                service_info["status"] = "stopped"
                
                # 移到历史记录
                if "history" not in state:
                    state["history"] = []
                state["history"].append(service_info)
                
                # 只保留最近50条历史记录
                if len(state["history"]) > 50:
                    state["history"] = state["history"][-50:]
                
                # 从活跃服务中移除
                del state["services"][service_name]
                self._save_services_state(state)
                
                return {
                    "success": True,
                    "service_name": service_name,
                    "pid": pid,
                    "stopped_at": service_info["stopped_at"],
                    "force_killed": force
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to stop service {service_name}",
                    "service_name": service_name,
                    "pid": pid
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "service_name": service_name
            }
    
    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """获取服务状态"""
        try:
            state = self._load_services_state()
            
            if service_name not in state["services"]:
                return {
                    "success": True,
                    "service_name": service_name,
                    "status": "not_found",
                    "running": False
                }
            
            service_info = state["services"][service_name].copy()
            pid = service_info.get("pid")
            
            # 检查进程是否真的在运行
            if self._is_process_running(pid):
                # 获取进程详细信息
                try:
                    process = psutil.Process(pid)
                    service_info.update({
                        "status": "running",
                        "running": True,
                        "cpu_percent": process.cpu_percent(),
                        "memory_info": process.memory_info()._asdict(),
                        "create_time": datetime.fromtimestamp(process.create_time()).isoformat(),
                        "num_threads": process.num_threads()
                    })
                except psutil.NoSuchProcess:
                    service_info.update({
                        "status": "not_running",
                        "running": False
                    })
            else:
                service_info.update({
                    "status": "not_running", 
                    "running": False
                })
            
            return {
                "success": True,
                "service_info": service_info
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "service_name": service_name
            }
    
    def list_running_services(self) -> Dict[str, Any]:
        """列出所有运行中的服务"""
        try:
            state = self._load_services_state()
            running_services = []
            stale_services = []
            
            for service_name, service_info in state["services"].items():
                pid = service_info.get("pid")
                if self._is_process_running(pid):
                    # 服务正在运行
                    service_status = service_info.copy()
                    service_status["actual_status"] = "running"
                    
                    # 添加进程信息
                    try:
                        process = psutil.Process(pid)
                        service_status.update({
                            "cpu_percent": process.cpu_percent(),
                            "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                            "running_time": datetime.now().timestamp() - process.create_time()
                        })
                    except psutil.NoSuchProcess:
                        pass
                    
                    running_services.append(service_status)
                else:
                    # 服务记录存在但进程不在运行
                    stale_services.append(service_name)
            
            return {
                "success": True,
                "running_count": len(running_services),
                "stale_count": len(stale_services),
                "running_services": running_services,
                "stale_services": stale_services,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def cleanup_stale_services(self) -> Dict[str, Any]:
        """清理无效的服务记录"""
        try:
            state = self._load_services_state()
            cleaned_services = []
            
            for service_name in list(state["services"].keys()):
                service_info = state["services"][service_name]
                pid = service_info.get("pid")
                
                if not self._is_process_running(pid):
                    # 进程不存在，清理记录
                    cleaned_info = service_info.copy()
                    cleaned_info["cleaned_at"] = datetime.now().isoformat()
                    cleaned_info["reason"] = "process_not_running"
                    
                    del state["services"][service_name]
                    cleaned_services.append(cleaned_info)
            
            self._save_services_state(state)
            
            return {
                "success": True,
                "cleaned_count": len(cleaned_services),
                "cleaned_services": cleaned_services,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_service_logs(self, service_name: str, lines: int = 50) -> Dict[str, Any]:
        """获取服务日志（如果有的话）"""
        try:
            state = self._load_services_state()
            
            if service_name not in state["services"]:
                return {
                    "success": False,
                    "error": f"Service {service_name} not found",
                    "service_name": service_name
                }
            
            service_info = state["services"][service_name]
            working_dir = service_info.get("working_dir", "/tmp")
            
            # 尝试查找日志文件
            log_files = [
                f"{working_dir}/{service_name}.log",
                f"/tmp/{service_name}.log",
                f"/var/log/{service_name}.log"
            ]
            
            logs = []
            for log_file in log_files:
                if os.path.exists(log_file):
                    try:
                        # 读取最后N行
                        with open(log_file, 'r') as f:
                            file_lines = f.readlines()
                            logs.extend(file_lines[-lines:])
                    except Exception:
                        continue
            
            return {
                "success": True,
                "service_name": service_name,
                "log_lines": len(logs),
                "logs": ''.join(logs) if logs else "No logs found",
                "log_files_checked": log_files
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "service_name": service_name
            }
    
    def _is_process_running(self, pid: Optional[int]) -> bool:
        """检查进程是否在运行"""
        if not pid:
            return False
        
        try:
            # 检查进程是否存在
            process = psutil.Process(pid)
            return process.is_running()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    def _stop_process(self, pid: int, force: bool = False) -> bool:
        """停止进程"""
        try:
            if force:
                # 强制杀死进程组
                os.killpg(pid, signal.SIGKILL)
            else:
                # 优雅停止
                os.killpg(pid, signal.SIGTERM)
                
                # 等待进程退出
                for _ in range(10):  # 等待最多10秒
                    if not self._is_process_running(pid):
                        return True
                    time.sleep(1)
                
                # 如果还没退出，强制杀死
                os.killpg(pid, signal.SIGKILL)
            
            return True
            
        except (OSError, ProcessLookupError):
            # 进程可能已经不存在了
            return True
        except Exception:
            return False
    
    def _load_services_state(self) -> Dict[str, Any]:
        """加载服务状态"""
        if not os.path.exists(self.services_state_file):
            return {
                "services": {},
                "history": [],
                "created_at": datetime.now().isoformat()
            }
        
        try:
            with open(self.services_state_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {
                "services": {},
                "history": [],
                "created_at": datetime.now().isoformat()
            }
    
    def _save_services_state(self, state: Dict[str, Any]) -> None:
        """保存服务状态"""
        state["last_updated"] = datetime.now().isoformat()
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self.services_state_file), exist_ok=True)
        
        with open(self.services_state_file, 'w') as f:
            json.dump(state, f, indent=2)