# 页面级多模态 RAG 方案

## 🎯 核心理念

**每个 PDF 页面 = 1 个 chunk**，页面内的图片和文字作为一个整体进行处理和检索。

## 📊 新旧方案对比

| 维度 | 旧方案（分离式） | 新方案（页面级） |
|------|----------------|----------------|
| **处理单位** | 文字/图片分离 | **页面整体** ✅ |
| **VLM 分析** | 图片单独分析，无上下文 | **页面级分析**，图+文一起 ✅ |
| **语义关联** | ❌ 无关联 | ✅ **强关联**（共享页面summary） |
| **图片描述** | "一个软件界面..." (泛泛) | "订单管理界面截图，展示了..." (精准) ✅ |
| **检索效果** | 图文分离，难以匹配 | **图文协同**，效果更好 ✅ |
| **存储结构** | N个文字 + M张图片 = N+M条记录 | **K个页面 = K条记录** ✅ |

## 🔄 新方案工作流程

### 1️⃣ 页面级多模态处理

```python
for each page in PDF:
    # 步骤1: 渲染整页为图片
    page_image = render_pdf_page(pdf_path, page_number)
    
    # 步骤2: VLM 分析整页（图+文）
    vlm_result = vlm_analyze(
        image=page_image,
        prompt=f"""
        分析这个PDF页面（第{page_num}页）。
        页面文字内容：{page_text}
        
        请提供：
        1. page_summary: 页面主题概括
        2. photo_1: 第1张图片的内容描述
        3. photo_2: 第2张图片的内容描述
        ...
        """
    )
    # 输出: {
    #   "page_summary": "订单管理界面操作说明",
    #   "photo_descriptions": [
    #     "订单管理主界面截图，显示左侧菜单、顶部搜索栏...",
    #     "订单详情弹窗界面..."
    #   ]
    # }
    
    # 步骤3: 提取并上传图片到 MinIO
    photo_urls = []
    for img in page.images:
        url = upload_to_minio(img)
        photo_urls.append(url)
    
    # 步骤4: 合并内容为统一文本
    combined_text = f"""
    【页面概要】{page_summary}
    
    【页面文字】
    {page_text}
    
    【页面图片】
    图片1: {photo_descriptions[0]}
      链接: {photo_urls[0]}
    图片2: {photo_descriptions[1]}
      链接: {photo_urls[1]}
    """
    
    # 步骤5: 生成 embedding
    embedding = embed(combined_text)
    
    # 步骤6: 存储为一条记录
    save_to_vector_db({
        'page_number': page_num,
        'text': combined_text,
        'embedding': embedding,
        'photo_urls': photo_urls,
        'metadata': {
            'page_summary': page_summary,
            'num_photos': len(photo_urls),
            'photo_descriptions': photo_descriptions
        }
    })
```

### 2️⃣ 存储结构

```json
{
  "id": "uuid",
  "user_id": "test_user",
  "text": "【页面概要】订单管理界面操作说明\n【页面文字】...\n【页面图片】图片1:...",
  "embedding": [0.1, 0.2, ...],
  "metadata": {
    "record_type": "page",
    "page_number": 1,
    "page_summary": "订单管理界面操作说明",
    "num_photos": 2,
    "photo_urls": [
      "https://minio.../page1_img0.png",
      "https://minio.../page1_img1.png"
    ],
    "photo_descriptions": [
      "订单管理主界面截图...",
      "订单详情弹窗界面..."
    ]
  }
}
```

### 3️⃣ 检索流程

```python
# 用户查询: "订单管理页面如何操作？"

# 1. 生成查询 embedding
query_embedding = embed("订单管理页面如何操作？")

# 2. 向量相似度搜索
results = vector_db.search(query_embedding, top_k=3)

# 3. 返回页面级结果
[
  {
    "page_number": 1,
    "page_summary": "订单管理界面操作说明",
    "text": "【页面概要】订单管理界面操作说明\n...",
    "similarity_score": 0.85,
    "photo_urls": [
      "https://minio.../page1_img0.png",
      "https://minio.../page1_img1.png"
    ],
    "num_photos": 2
  },
  ...
]

# ✅ 优势：
# - 文字和图片一起匹配
# - 图片描述有上下文，更准确
# - 可以直接获取图片 URLs
```

### 4️⃣ 生成流程

```python
# 构建上下文（页面级）
context = """
## 相关页面内容：

[页面 1] (页码: 1)
摘要: 订单管理界面操作说明
内容: 【页面概要】...
包含 2 张图片:
  图片1: https://minio.../page1_img0.png
  图片2: https://minio.../page1_img1.png

[页面 2] (页码: 2)
...
"""

# LLM 生成答案
answer = llm_generate(
    query="订单管理页面如何操作？",
    context=context
)

# ✅ 优势：
# - LLM 看到完整的页面信息
# - 可以在答案中引用图片 URLs
# - 理解图文关系
```

## 🎨 关键特性

### 1. VLM 看到完整页面

**旧方案**：
```
图片1（单独） → VLM → "一个软件界面" ❌
```

**新方案**：
```
整个页面（文字+图片） → VLM → "订单管理界面，左侧导航菜单..." ✅
```

### 2. 图文语义强关联

```
embedding(【页面概要】+ 页面文字 + 图片描述)
       ↓
    一个向量
       ↓
检索时：文字和图片一起匹配 ✅
```

### 3. 图片 URLs 在 metadata 中

```python
# 检索结果直接包含图片 URLs
result = {
    'page_number': 1,
    'photo_urls': [
        'https://minio.../img1.png',
        'https://minio.../img2.png'
    ]
}

# LLM 可以在答案中引用
"请参考图片: https://minio.../img1.png"
```

## 📈 性能优势

### 并发处理

```python
# 页面级并发
max_concurrent_pages = 3  # 同时处理3个页面

# 每个页面包含:
# - VLM 分析整页（~5s）
# - 图片上传 MinIO（并行）
# - Embedding 生成（~1s）

# 总时间 ≈ (页面数 / 并发数) × 单页处理时间
```

### 存储优化

- **旧方案**: 55个文字块 + 10张图片 = **65条记录**
- **新方案**: 5个页面 = **5条记录** ✅

检索更快，存储更少！

## 🧪 测试配置

```python
config = {
    'top_k_results': 5,
    'max_concurrent_pages': 2,  # 页面级并发数
    'max_pages': 5  # 快速测试：只处理5页
}
```

## 🎯 预期效果

### 摄取

```
📄 页面数: 5
🖼️ 图片数: 20
📊 总记录数: 5  (每页1条)
⏱️ 处理时间: ~60s
```

### 检索

```
查询: "订单管理页面如何操作？"

✅ 检索成功:
   📄 页面结果: 3 个
   🖼️ 图片总数: 8 张

[1] 页1 (相似度:0.85)
    摘要: 订单管理界面操作说明
    包含 2 张图片
      图1: https://minio.../page1_img0.png
      图2: https://minio.../page1_img1.png
```

### 生成

```
📊 来源统计:
   页面来源: 3 个
   图片总数: 8 张

📄 相关页面和图片:
   [页面1] 第1页: 订单管理界面操作说明...
       图片1: https://minio.../page1_img0.png
       图片2: https://minio.../page1_img1.png
```

## 💡 优势总结

| 优势 | 说明 |
|------|------|
| ✅ **语义完整性** | 页面作为整体，保持图文关系 |
| ✅ **VLM 精准度** | 看到完整上下文，描述更准确 |
| ✅ **检索效果** | 图文协同匹配，相关性更强 |
| ✅ **存储效率** | 记录数大幅减少（5 vs 65） |
| ✅ **用户体验** | 直接获取图片 URLs，一步到位 |
| ✅ **扩展性** | 易于支持更多页面级特性（表格、图表等） |

## 🚀 下一步

测试新方案：

```bash
cd /Users/xenodennis/Documents/Fun/isA_MCP
python test_custom_rag_service.py
```

---

**方案设计**: 根据用户建议优化  
**实现日期**: 2025-10-11  
**状态**: ✅ 已实现，待测试

