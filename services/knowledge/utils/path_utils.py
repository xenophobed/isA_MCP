# app/services/utils/path_utils.py
from typing import List

def build_category_path(parent_path: str, name: str) -> str:
    """构建分类路径"""
    if not parent_path or parent_path == "/":
        return f"/{name}"
    return f"{parent_path}/{name}"

def split_path(path: str) -> List[str]:
    """分割路径为各级名称"""
    return [p for p in path.split("/") if p]