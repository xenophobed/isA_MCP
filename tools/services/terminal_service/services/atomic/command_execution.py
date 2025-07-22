"""
命令执行原子服务
最基础的系统命令执行操作，不依赖任何其他服务
"""

import subprocess
import shlex
import os
from typing import Dict, Any, Optional, List
from datetime import datetime


class CommandExecution:
    """命令执行原子服务"""
    
    @staticmethod
    def execute_command(
        command: str, 
        cwd: Optional[str] = None, 
        timeout: int = 30,
        capture_output: bool = True,
        shell: bool = False
    ) -> Dict[str, Any]:
        """执行系统命令 - 最基础的原子操作"""
        try:
            start_time = datetime.now()
            
            # 安全处理命令
            if not shell:
                # 将命令字符串分割为参数列表
                cmd_args = shlex.split(command)
            else:
                cmd_args = command
            
            # 执行命令
            result = subprocess.run(
                cmd_args,
                cwd=cwd,
                timeout=timeout,
                capture_output=capture_output,
                text=True,
                shell=shell
            )
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            return {
                "success": result.returncode == 0,
                "command": command,
                "return_code": result.returncode,
                "stdout": result.stdout if capture_output else "",
                "stderr": result.stderr if capture_output else "",
                "execution_time": execution_time,
                "cwd": cwd,
                "timestamp": start_time.isoformat()
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "command": command,
                "error": f"Command timed out after {timeout} seconds",
                "return_code": -1,
                "execution_time": timeout,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "command": command,
                "error": str(e),
                "return_code": -1,
                "timestamp": datetime.now().isoformat()
            }
    
    @staticmethod
    def execute_shell_command(
        command: str, 
        cwd: Optional[str] = None, 
        timeout: int = 30
    ) -> Dict[str, Any]:
        """执行shell命令（允许管道、重定向等）"""
        return CommandExecution.execute_command(
            command=command,
            cwd=cwd,
            timeout=timeout,
            shell=True
        )
    
    @staticmethod
    def check_command_exists(command: str) -> Dict[str, Any]:
        """检查命令是否存在"""
        try:
            result = CommandExecution.execute_command(f"which {command}")
            
            return {
                "success": True,
                "command": command,
                "exists": result["success"],
                "path": result["stdout"].strip() if result["success"] else None,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "command": command,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    @staticmethod
    def execute_batch_commands(
        commands: List[str], 
        cwd: Optional[str] = None,
        stop_on_error: bool = True
    ) -> Dict[str, Any]:
        """批量执行命令"""
        try:
            results = []
            all_success = True
            
            for i, command in enumerate(commands):
                result = CommandExecution.execute_command(command, cwd)
                results.append({
                    "index": i,
                    "command": command,
                    "result": result
                })
                
                if not result["success"]:
                    all_success = False
                    if stop_on_error:
                        break
            
            return {
                "success": all_success,
                "total_commands": len(commands),
                "executed_commands": len(results),
                "results": results,
                "stop_on_error": stop_on_error,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "total_commands": len(commands),
                "timestamp": datetime.now().isoformat()
            } 