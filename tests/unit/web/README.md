# Web Services Test Structure

本目录包含Web服务架构的完整测试套件，按照服务层次结构组织。

## 📁 目录结构

### `/tools/` - Web工具层测试
MCP工具的端到端功能测试，对应4步工作流程：

- `test_web_search.py` - **Step 1**: 搜索和过滤功能测试
- `test_web_automation.py` - **Step 2**: Web自动化功能测试  
- `test_web_crawl_extract.py` - **Step 3**: 爬取提取功能测试（基础）
- `test_web_crawl_stealth.py` - **Step 3**: 爬取提取功能测试（增强隐身）
- `test_web_synthesis.py` - **Step 4**: 合成生成功能测试

### `/engines/` - 引擎层测试
核心处理引擎的功能测试：

- `test_search_engine.py` - 搜索引擎功能测试
- `test_extraction_engine.py` - 提取引擎功能测试
- `test_search_link_extraction.py` - 搜索链接提取功能测试

### `/strategies/` - 策略层测试
不同策略模式的功能测试：

#### `/strategies/detection/` - 检测策略
- `test_intelligent_element_detection.py` - 智能元素检测测试
- `test_selector_analyzer.py` - 选择器分析器测试

#### `/strategies/extraction/` - 提取策略  
- `test_extraction_strategies.py` - 提取策略综合测试

#### `/strategies/filtering/` - 过滤策略
- `test_ai_enhanced_filtering.py` - AI增强过滤测试
- `test_content_filters.py` - 内容过滤器测试

### `/services/` - 服务层测试
底层服务组件的功能测试：

- `test_stealth_manager.py` - 隐身管理器测试
- `test_human_behavior.py` - 人类行为模拟测试
- `test_ai_enhanced_integration.py` - AI增强集成测试

### `/deprecated/` - 废弃测试
不再使用或过时的测试文件：

- `test_web_login.py` - 登录自动化测试（已废弃）

## 🧪 测试覆盖范围

### 功能测试覆盖
- ✅ **完整4步工作流程** - Search → Automation → Extract → Synthesis
- ✅ **多级隐身技术** - StealthManager (basic/medium/high)
- ✅ **人类行为模拟** - HumanBehavior (打字、鼠标、滚动、阅读)
- ✅ **LLM驱动提取** - 智能内容理解和结构化提取
- ✅ **语义过滤** - Embedding相似度过滤
- ✅ **多格式输出** - Markdown, JSON, Summary, Report
- ✅ **智能网站检测** - 根据网站类型调整策略

### 测试类型
- **单元测试** - 单个组件功能验证
- **集成测试** - 组件间协作验证  
- **端到端测试** - 完整工作流程验证
- **性能测试** - 响应时间和准确率测试

## 🚀 运行测试

### 运行单个测试
```bash
# 运行特定工具测试
python tests/unit/web/tools/test_web_search.py

# 运行特定服务测试  
python tests/unit/web/services/test_stealth_manager.py
```

### 运行分类测试
```bash
# 运行所有工具测试
pytest tests/unit/web/tools/

# 运行所有引擎测试
pytest tests/unit/web/engines/

# 运行所有服务测试
pytest tests/unit/web/services/
```

### 运行完整测试套件
```bash
# 运行所有Web服务测试
pytest tests/unit/web/ -v

# 运行带覆盖率报告
pytest tests/unit/web/ --cov=tools.services.web_services
```

## 📊 测试质量指标

### 当前状态
- **总测试数**: 71个测试用例
- **通过率**: 93% (66/71)
- **代码覆盖率**: >85%
- **性能基准**: 平均 8.5秒/页面

### 质量标准
- ✅ 所有核心功能必须有测试覆盖
- ✅ 集成测试验证端到端流程
- ✅ 性能测试确保响应时间合理
- ✅ 错误处理测试验证健壮性

## 🔄 维护指南

### 添加新测试
1. 确定测试类型和层次
2. 放置到对应目录结构中
3. 遵循命名约定：`test_<功能名称>.py`
4. 包含完整的文档和断言

### 更新现有测试
1. 保持测试与代码同步
2. 更新测试文档和注释
3. 验证测试覆盖率不下降
4. 运行回归测试确保稳定性

---

**最后更新**: 2025-06-29  
**维护人员**: Web Services Team