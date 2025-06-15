import asyncio
import json
import sqlite3
import os
from datetime import datetime
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Dict, List, Optional, Any
import numpy as np
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP
from langchain_openai import OpenAIEmbeddings

# 加载环境变量
load_dotenv(".env.local")

# 数据库初始化函数
def init_database():
    """初始化数据库表"""
    conn = sqlite3.connect("memory.db")
    
    # 删除已存在的表以确保结构正确
    conn.execute("DROP TABLE IF EXISTS memories")
    conn.execute("DROP TABLE IF EXISTS vector_memories")
    
    # 创建基本记忆表 - 确保包含所有必需的列
    conn.execute("""
    CREATE TABLE memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT NOT NULL UNIQUE,
        value TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'general',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        importance INTEGER DEFAULT 1
    )
    """)
    
    # 创建向量存储表
    conn.execute("""
    CREATE TABLE vector_memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT NOT NULL UNIQUE,
        value TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'general',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        importance INTEGER DEFAULT 1,
        embedding BLOB NOT NULL
    )
    """)
    
    # 创建索引以提高查询性能
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_vector_memories_category ON vector_memories(category)")
    
    conn.commit()
    conn.close()
    print("数据库初始化完成")

# 数据库升级函数 - 如果不想删除现有数据
def upgrade_database():
    """升级现有数据库结构"""
    conn = sqlite3.connect("memory.db")
    
    try:
        # 检查 memories 表是否存在 updated_at 列
        cursor = conn.execute("PRAGMA table_info(memories)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'updated_at' not in columns:
            print("添加 updated_at 列到 memories 表...")
            conn.execute("ALTER TABLE memories ADD COLUMN updated_at TEXT DEFAULT ''")
            # 为现有记录设置 updated_at
            now = datetime.now().isoformat()
            conn.execute("UPDATE memories SET updated_at = ? WHERE updated_at = ''", (now,))
            
        if 'category' not in columns:
            print("添加 category 列到 memories 表...")
            conn.execute("ALTER TABLE memories ADD COLUMN category TEXT DEFAULT 'general'")
            
        if 'importance' not in columns:
            print("添加 importance 列到 memories 表...")
            conn.execute("ALTER TABLE memories ADD COLUMN importance INTEGER DEFAULT 1")
        
        conn.commit()
        print("数据库升级完成")
        
    except Exception as e:
        print(f"数据库升级失败: {e}")
        # 如果升级失败，可以选择重新初始化
        print("正在重新初始化数据库...")
        conn.close()
        init_database()
        return
    
    conn.close()

# 创建MCP服务器
mcp = FastMCP("Memory Management System")

# 基本记忆管理工具
@mcp.tool()
async def remember(key: str, value: str, category: str = "general", importance: int = 1) -> str:
    """存储一个新的记忆"""
    db_conn = sqlite3.connect("memory.db")
    now = datetime.now().isoformat()
    
    try:
        # 首先检查记录是否存在
        cursor = db_conn.execute("SELECT id FROM memories WHERE key = ?", (key,))
        existing = cursor.fetchone()
        
        if existing:
            # 更新现有记录
            db_conn.execute(
                "UPDATE memories SET value = ?, category = ?, updated_at = ?, importance = ? WHERE key = ?",
                (value, category, now, importance, key)
            )
        else:
            # 插入新记录
            db_conn.execute(
                "INSERT INTO memories (key, value, category, created_at, updated_at, importance) VALUES (?, ?, ?, ?, ?, ?)",
                (key, value, category, now, now, importance)
            )
        
        db_conn.commit()
        action = "更新" if existing else "存储"
        return f"✓ 已{action}: {key} = {value} (类别: {category}, 重要性: {importance})"
    
    except Exception as e:
        return f"❌ 记忆存储失败: {str(e)}"
    finally:
        db_conn.close()

@mcp.tool()
async def recall(key: str) -> str:
    """检索一个记忆"""
    db_conn = sqlite3.connect("memory.db")
    
    try:
        cursor = db_conn.execute(
            "SELECT value, category, created_at, importance, updated_at FROM memories WHERE key = ? ORDER BY importance DESC LIMIT 1", 
            (key,)
        )
        result = cursor.fetchone()
        
        if result:
            value, category, created_at, importance, updated_at = result
            return f"🧠 记忆: {key} = {value}\n  类别: {category}\n  重要性: {importance}\n  创建时间: {created_at}\n  更新时间: {updated_at}"
        
        return f"❓ 没有找到关于 '{key}' 的记忆"
    
    except Exception as e:
        return f"❌ 记忆检索失败: {str(e)}"
    finally:
        db_conn.close()

@mcp.tool()
async def recall_by_category(category: str, limit: int = 5) -> str:
    """按类别检索记忆"""
    db_conn = sqlite3.connect("memory.db")
    
    try:
        cursor = db_conn.execute(
            "SELECT key, value, importance, created_at FROM memories WHERE category = ? ORDER BY importance DESC, created_at DESC LIMIT ?", 
            (category, limit)
        )
        results = cursor.fetchall()
        
        if not results:
            return f"📂 没有找到类别为 '{category}' 的记忆"
        
        memories = []
        for key, value, importance, created_at in results:
            memories.append(f"  • {key}: {value} (重要性: {importance})")
        
        memories_text = "\n".join(memories)
        return f"📂 类别 '{category}' 的记忆 ({len(results)}条):\n{memories_text}"
    
    except Exception as e:
        return f"❌ 按类别检索失败: {str(e)}"
    finally:
        db_conn.close()

@mcp.tool()
async def forget(key: str) -> str:
    """删除一个记忆"""
    db_conn = sqlite3.connect("memory.db")
    
    try:
        # 从长期记忆中删除
        cursor = db_conn.execute("DELETE FROM memories WHERE key = ?", (key,))
        
        # 同时从向量记忆中删除
        db_conn.execute("DELETE FROM vector_memories WHERE key = ?", (key,))
        db_conn.commit()
        
        if cursor.rowcount > 0:
            return f"🗑️ 已删除关于 '{key}' 的记忆"
        return f"❓ 没有找到关于 '{key}' 的记忆可删除"
    
    except Exception as e:
        return f"❌ 记忆删除失败: {str(e)}"
    finally:
        db_conn.close()

@mcp.tool()
async def summarize_memories() -> str:
    """总结所有记忆"""
    db_conn = sqlite3.connect("memory.db")
    
    try:
        # 获取基本统计
        cursor = db_conn.execute("SELECT COUNT(*) FROM memories")
        total_memories = cursor.fetchone()[0]
        
        cursor = db_conn.execute("SELECT COUNT(*) FROM vector_memories")
        total_vector_memories = cursor.fetchone()[0]
        
        # 获取类别统计
        cursor = db_conn.execute("SELECT category, COUNT(*) as count FROM memories GROUP BY category ORDER BY count DESC")
        categories = cursor.fetchall()
        
        # 获取最重要的记忆
        cursor = db_conn.execute("SELECT key, value, importance FROM memories ORDER BY importance DESC LIMIT 5")
        important = cursor.fetchall()
        
        # 获取最近的记忆
        cursor = db_conn.execute("SELECT key, value, created_at FROM memories ORDER BY created_at DESC LIMIT 5")
        recent = cursor.fetchall()
        
        # 构建总结
        summary = f"📊 记忆系统总结\n{'='*40}\n\n"
        summary += f"📈 总体统计:\n"
        summary += f"  • 总记忆数: {total_memories}\n"
        summary += f"  • 向量记忆数: {total_vector_memories}\n\n"
        
        if categories:
            summary += f"📂 类别分布:\n"
            for category, count in categories:
                summary += f"  • {category}: {count}条\n"
            summary += "\n"
        
        if important:
            summary += f"⭐ 最重要的记忆:\n"
            for key, value, importance in important:
                summary += f"  • {key}: {value[:50]}... (重要性: {importance})\n"
            summary += "\n"
        
        if recent:
            summary += f"🕐 最近的记忆:\n"
            for key, value, created_at in recent:
                summary += f"  • {key}: {value[:50]}... ({created_at[:16]})\n"
        
        return summary
    
    except Exception as e:
        return f"❌ 记忆总结失败: {str(e)}"
    finally:
        db_conn.close()

# 向量记忆工具
@mcp.tool()
async def remember_with_embedding(key: str, value: str, category: str = "general", importance: int = 1) -> str:
    """存储一个带有嵌入向量的记忆"""
    # 初始化嵌入模型
    try:
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            dimensions=1536
        )
    except Exception as e:
        return f"❌ 嵌入模型初始化失败: {str(e)}"
    
    db_conn = sqlite3.connect("memory.db")
    
    try:
        now = datetime.now().isoformat()
        
        # 生成嵌入向量
        embedding_vector = embeddings.embed_query(value)
        embedding_bytes = np.array(embedding_vector).tobytes()
        
        # 检查记录是否存在
        cursor = db_conn.execute("SELECT id FROM vector_memories WHERE key = ?", (key,))
        existing = cursor.fetchone()
        
        if existing:
            # 更新现有记录
            db_conn.execute(
                "UPDATE vector_memories SET value = ?, category = ?, updated_at = ?, importance = ?, embedding = ? WHERE key = ?",
                (value, category, now, importance, embedding_bytes, key)
            )
        else:
            # 插入新记录
            db_conn.execute(
                "INSERT INTO vector_memories (key, value, category, created_at, updated_at, importance, embedding) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (key, value, category, now, now, importance, embedding_bytes)
            )
        
        db_conn.commit()
        action = "更新" if existing else "存储"
        return f"✓ 已{action}向量记忆: {key} (类别: {category}, 重要性: {importance})"
    
    except Exception as e:
        return f"❌ 向量记忆存储失败: {str(e)}"
    finally:
        db_conn.close()

@mcp.tool()
async def semantic_search(query: str, limit: int = 5, threshold: float = 0.1) -> str:
    """基于语义相似度搜索记忆"""
    # 初始化嵌入模型
    try:
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            dimensions=1536
        )
    except Exception as e:
        return f"❌ 嵌入模型初始化失败: {str(e)}"
    
    db_conn = sqlite3.connect("memory.db")
    
    try:
        # 生成查询的嵌入向量
        query_embedding = np.array(embeddings.embed_query(query))
        
        # 获取所有记忆的向量
        cursor = db_conn.execute("SELECT id, key, value, category, importance, embedding FROM vector_memories")
        results = cursor.fetchall()
        
        if not results:
            return "📭 没有找到任何向量记忆"
        
        # 计算相似度并排序
        similarities = []
        for id, key, value, category, importance, embedding_bytes in results:
            try:
                embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
                # 计算余弦相似度
                similarity = np.dot(query_embedding, embedding) / (np.linalg.norm(query_embedding) * np.linalg.norm(embedding))
                
                # 只保留超过阈值的结果
                if similarity >= threshold:
                    similarities.append((similarity, key, value, category, importance))
            except Exception as e:
                print(f"处理向量时出错: {e}")
                continue
        
        # 按相似度排序并返回前limit个
        similarities.sort(reverse=True)
        top_memories = similarities[:limit]
        
        if not top_memories:
            return f"🔍 没有找到与 '{query}' 相关的记忆 (相似度阈值: {threshold})"
        
        result = f"🔍 与 '{query}' 相关的记忆 ({len(top_memories)}条):\n"
        for i, (similarity, key, value, category, importance) in enumerate(top_memories, 1):
            result += f"  {i}. {key} (相似度: {similarity:.3f}, 重要性: {importance})\n"
            result += f"     类别: {category}\n"
            result += f"     内容: {value[:100]}{'...' if len(value) > 100 else ''}\n\n"
        
        return result
    
    except Exception as e:
        return f"❌ 语义搜索失败: {str(e)}"
    finally:
        db_conn.close()

@mcp.tool()
async def update_memory_importance(key: str, new_importance: int) -> str:
    """更新记忆的重要性"""
    db_conn = sqlite3.connect("memory.db")
    
    try:
        now = datetime.now().isoformat()
        
        # 更新基本记忆表
        cursor = db_conn.execute(
            "UPDATE memories SET importance = ?, updated_at = ? WHERE key = ?",
            (new_importance, now, key)
        )
        
        # 更新向量记忆表
        db_conn.execute(
            "UPDATE vector_memories SET importance = ?, updated_at = ? WHERE key = ?",
            (new_importance, now, key)
        )
        
        db_conn.commit()
        
        if cursor.rowcount > 0:
            return f"✓ 已更新 '{key}' 的重要性为 {new_importance}"
        return f"❓ 没有找到关于 '{key}' 的记忆"
    
    except Exception as e:
        return f"❌ 更新重要性失败: {str(e)}"
    finally:
        db_conn.close()

# 提示模板
@mcp.prompt()
def with_memory_context(query: str) -> str:
    """包含用户历史记忆的提示模板"""
    return f"""
系统: 你是一个具有记忆能力的AI助手。在回答用户问题时，请考虑以下记忆信息。

用户问题: {query}

可用的记忆工具:
- remember: 存储新记忆
- recall: 检索特定记忆
- recall_by_category: 按类别检索记忆
- forget: 删除记忆
- summarize_memories: 总结所有记忆
- remember_with_embedding: 存储向量记忆
- semantic_search: 语义搜索记忆
- update_memory_importance: 更新记忆重要性

请根据用户的问题，合理使用这些工具来提供有帮助的回答。
"""

# 启动服务器
if __name__ == "__main__":
    print("正在初始化数据库...")
    
    # 检查数据库是否存在，如果存在则升级，否则初始化
    if os.path.exists("memory.db"):
        upgrade_database()
    else:
        init_database()
    
    print("启动记忆管理服务器...")
    mcp.run(transport="streamable-http")