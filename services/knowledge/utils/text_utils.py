# app/services/utils/text_utils.py
import re
from typing import List

def clean_text(text: str) -> str:
    """清理文本"""
    # 移除多余空白
    text = re.sub(r'\s+', ' ', text).strip()
    # 统一换行符
    text = text.replace('\r\n', '\n')
    return text

def split_sentences(text: str) -> List[str]:
    """分割句子"""
    # 简单的句子分割
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

def calculate_token_count(text: str) -> int:
    """计算token数量（简化版）"""
    # 这里用简单的空格分割，实际应使用proper tokenizer
    return len(text.split())