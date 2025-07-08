# Vision Analyzer - 两层AI视觉分析系统

## 概述

Vision Analyzer 是一个基于两层AI架构的智能网页视觉分析系统，结合了ISA Vision (OmniParser) 的精确坐标检测和OpenAI Vision的语义理解能力，为网页自动化提供高精度的元素定位和分析。

## 🏗️ 架构设计

### 两层AI架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Vision Analyzer                        │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: ISA Vision (OmniParser UI Detection)            │
│  • 精确UI元素坐标检测                                       │
│  • 元素类型识别 (button, input, link等)                    │
│  • 可交互性检测                                            │
│  • 置信度评分                                              │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: OpenAI Vision (语义映射)                        │
│  • 业务逻辑语义理解                                        │
│  • 元素功能映射 (username, password, submit等)             │
│  • 上下文分析                                              │
│  • 智能推理                                                │
├─────────────────────────────────────────────────────────────┤
│  Fallback: ISA-Only Mapping                              │
│  • 当OpenAI分析失败时的后备方案                            │
│  • 基于内容和类型的基础映射                                 │
│  • 保证系统稳定性                                          │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 主要功能

### 1. 登录表单检测 (`identify_login_form`)
- **输入**: Playwright页面对象
- **输出**: 登录元素字典 (username, password, submit)
- **特点**: 
  - 🎯 两层AI精确定位
  - 💾 结果缓存优化
  - ⚡ 预配置站点支持
  - 🔄 智能降级方案

### 2. 搜索表单检测 (`identify_search_form`)
- **输入**: Playwright页面对象
- **输出**: 搜索元素字典 (input, submit)
- **特点**:
  - 🔍 语义搜索理解
  - 📋 多种搜索框格式支持
  - 🎨 现代UI适配

### 3. 导航元素分析 (`analyze_ui_elements`)
- **输入**: 页面对象和任务类型
- **输出**: 导航元素结构化数据
- **特点**:
  - 🧭 智能导航分类
  - 🔗 链接层次分析
  - 📱 响应式布局支持

### 4. 下载链接检测 (`identify_download_links`)
- **输入**: Playwright页面对象
- **输出**: 下载链接列表
- **特点**:
  - 📥 多文件类型支持
  - 🎯 精确坐标定位
  - 📊 置信度评分

## 🛠️ 技术实现

### ISA Vision Layer (第一层)
```python
# ISA OmniParser UI检测调用
isa_result = await self.client.invoke(
    input_data=screenshot_path,
    task="detect_ui_elements",
    service_type="vision", 
    model="isa-omniparser-ui-detection",
    provider="isa"
)
```

### OpenAI Vision Layer (第二层)
```python
# OpenAI语义分析调用
openai_result = await self.client.invoke(
    screenshot_path,
    "analyze", 
    "vision",
    prompt=semantic_prompt
)
```

### 缓存系统
- **L1 缓存**: 预配置站点元素 (即时响应)
- **L2 缓存**: 历史分析结果 (快速响应)
- **L3 缓存**: AI分析结果 (准确响应)

## 📊 测试结果

### 全面测试通过率: 100% (4/4)

```
🎯 Overall: 4/4 tests passed
🎉 All vision analyzer tests passed!
✅ Two-layer AI analysis system working correctly!
🚀 Ready for production use!
```

#### 详细测试结果:

1. **登录检测**: ✅ 100% 成功率
   - 检测到 3/3 元素
   - 坐标: username(958,262), password(958,349), submit(960,412)
   - 置信度: 0.90 (OpenAI语义分析)

2. **搜索检测**: ✅ 100% 成功率
   - 检测到 2/2 元素
   - 坐标: input(909,167), submit(1157,167)
   - 置信度: 0.90 (OpenAI语义分析)

3. **导航检测**: ✅ 结构化导航分析
   - 识别导航链接、按钮、菜单容器
   - 支持语义分类和层次结构

4. **链接检测**: ✅ 多种检测方式
   - 传统选择器 + AI视觉分析
   - 文件类型智能识别

## 🚀 使用示例

### 基础使用
```python
from vision_analyzer import VisionAnalyzer

analyzer = VisionAnalyzer()

# 登录表单检测
login_elements = await analyzer.identify_login_form(page)
print(f"找到 {len(login_elements)} 个登录元素")

# 搜索表单检测
search_elements = await analyzer.identify_search_form(page)
print(f"找到 {len(search_elements)} 个搜索元素")

# 清理资源
await analyzer.close()
```

## 📝 API 参考

### 主要方法

| 方法 | 描述 | 输入 | 输出 |
|------|------|------|------|
| `identify_login_form(page)` | 登录表单检测 | Page对象 | Dict[str, Any] |
| `identify_search_form(page)` | 搜索表单检测 | Page对象 | Dict[str, Any] |
| `analyze_ui_elements(page, task_type)` | 通用UI分析 | Page对象, 任务类型 | Dict[str, Any] |
| `identify_download_links(page)` | 下载链接检测 | Page对象 | List[Dict[str, str]] |
| `get_cache_stats()` | 缓存统计 | 无 | Dict[str, Any] |
| `close()` | 资源清理 | 无 | None |

### 返回格式

#### 登录元素格式
```python
{
    "username": {
        "type": "coordinate",
        "x": 958,
        "y": 262,
        "action": "type",
        "description": "OpenAI semantic: email input field",
        "confidence": 0.90,
        "source": "openai_semantic"
    },
    "password": { ... },
    "submit": { ... }
}
```

---

*Vision Analyzer v2.0 - 基于两层AI架构的智能网页视觉分析系统*