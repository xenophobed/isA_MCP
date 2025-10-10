# Test Plan Service 编排架构

## 服务流程重构方案

### 当前问题
1. **服务分散且重复**：多个extractor做类似的事情
2. **数据流不清晰**：输入输出格式不统一
3. **缺少关键服务**：没有独立的PICS提取和Excel输出服务

### 重构后的服务架构

```
用户上传Excel
     ↓
┌────────────────────────────────────────┐
│  1. PICS Extraction Service            │
│  输入: Excel文件                        │
│  输出: PICSExtractionResult            │
│  - 2738个TRUE项目                      │
│  - Band信息提取                        │
│  - Feature信息提取                     │
└────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────┐
│  2. Condition Evaluation Service       │
│  输入: PICS TRUE项目                    │
│  处理: 对照DuckDB中的conditions        │
│  输出: 匹配的test_ids                  │
└────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────┐
│  3. Test Mapping Service               │
│  输入: 36.521-2格式test_ids            │
│  处理: 映射到36.521-1格式               │
│  输出: 标准化test_ids                  │
└────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────┐
│  4. Parameter Expansion Service        │
│  输入: test_ids + band参数              │
│  处理: 数学优化展开                    │
│  输出: 测试实例列表                    │
└────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────┐
│  5. Validation Service                 │
│  输入: 测试实例                        │
│  处理: PTCRB/GCF标准验证               │
│  输出: 合规性报告                      │
└────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────┐
│  6. Excel Generation Service           │
│  输入: 验证后的测试计划                │
│  输出: 标准化Excel文件                 │
└────────────────────────────────────────┘
```

## 核心服务定义

### 1. PICS Extraction Service (✅ 已实现)
- **位置**: `services/core/pics_extraction_service.py`
- **功能**: 从用户Excel提取PICS TRUE项目
- **输入**: Interlab Excel文件
- **输出**: 
  - PICSExtractionResult对象
  - 2738个TRUE项目（已验证）
  - Band和Feature信息

### 2. Condition Evaluation Service (需要整合)
- **当前**: `services/extractor/project_pics_extractor.py`
- **整合**: 
  - `services/processor/corrected_interlab_reader.py`
  - `services/extractor/applicability_extractor.py`
- **目标**: 统一的条件评估服务

### 3. Test Mapping Service (需要优化)
- **当前**: `services/extractor/test_mapping_extractor.py`
- **问题**: 映射规则不完整
- **改进**: 增强36.521-2到36.521-1的映射

### 4. Parameter Expansion Service (需要重构)
- **当前**: `services/extractor/parameter_expansion_engine.py`
- **问题**: 过于复杂，优化策略不清晰
- **改进**: 简化接口，明确优化策略

### 5. Validation Service (需要创建)
- **参考**: test01.ipynb中的PTCRB验证逻辑
- **功能**: 标准合规性验证
- **输出**: 覆盖率、精确率、F1分数

### 6. Excel Generation Service (需要创建)
- **功能**: 生成标准化的测试计划Excel
- **格式**: 按照PTCRB/GCF要求的格式

## 需要删除/整合的冗余服务

### 冗余的Extractors
1. `ai_dependency_logic_extractor.py` - 功能不明确
2. `band_mapping_extractor_v2.py` - 可以整合到PICS extraction
3. `applicability_extractor.py` - 整合到Condition Evaluation

### 冗余的Parsers
1. `csv_parser.py` - 很少使用
2. `excel_parser.py` - 可以整合到PICS extraction
3. `document_parser.py` - 过于复杂，支持太多格式

### 冗余的Processors
1. `corrected_interlab_reader.py` - 功能与PICS extraction重复

## 实施计划

1. **第一阶段**: 清理和整合
   - [x] 创建统一的PICS Extraction Service
   - [ ] 整合Condition Evaluation逻辑
   - [ ] 删除冗余的extractors

2. **第二阶段**: 优化核心流程
   - [ ] 优化Test Mapping Service
   - [ ] 简化Parameter Expansion
   - [ ] 创建Validation Service

3. **第三阶段**: 完善输出
   - [ ] 创建Excel Generation Service
   - [ ] 实现标准化输出格式
   - [ ] 添加报告生成功能

## API接口标准化

### 统一的数据格式
```python
@dataclass
class ServiceInput:
    """标准服务输入"""
    data: Any
    metadata: Dict[str, Any]
    config: Optional[Dict[str, Any]] = None

@dataclass 
class ServiceOutput:
    """标准服务输出"""
    success: bool
    data: Any
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### 服务接口规范
```python
class BaseService(ABC):
    """所有服务的基类"""
    
    @abstractmethod
    def process(self, input: ServiceInput) -> ServiceOutput:
        """处理输入并返回输出"""
        pass
    
    @abstractmethod
    def validate_input(self, input: ServiceInput) -> bool:
        """验证输入的有效性"""
        pass
```

## 数据流示例

```python
# 1. PICS提取
pics_service = PICSExtractionService()
pics_result = pics_service.extract_from_excel("user_excel.xlsx")
# 输出: 2738个TRUE项目

# 2. 条件评估
condition_service = ConditionEvaluationService()
test_ids = condition_service.evaluate(pics_result.pics_items)
# 输出: 匹配的test_ids

# 3. 测试映射
mapping_service = TestMappingService()
mapped_ids = mapping_service.map_to_standard(test_ids)
# 输出: 36.521-1格式的test_ids

# 4. 参数展开
expansion_service = ParameterExpansionService()
test_instances = expansion_service.expand(mapped_ids, pics_result.band_info)
# 输出: 展开的测试实例

# 5. 验证
validation_service = ValidationService()
validation_result = validation_service.validate_against_ptcrb(test_instances)
# 输出: 合规性报告

# 6. Excel生成
excel_service = ExcelGenerationService()
excel_service.generate(test_instances, validation_result, "output.xlsx")
# 输出: 标准化Excel文件
```

## 关键改进点

1. **数据流清晰**: 每个服务有明确的输入输出
2. **职责单一**: 每个服务只做一件事
3. **可测试性**: 每个服务可以独立测试
4. **可扩展性**: 容易添加新的服务或修改现有服务
5. **标准化**: 统一的接口和数据格式

## 性能优化

1. **批处理**: 支持批量处理多个文件
2. **缓存**: 缓存DuckDB查询结果
3. **并行处理**: 参数展开可以并行化
4. **增量更新**: 只处理变化的部分

## 监控和日志

1. **统一日志格式**: 使用结构化日志
2. **性能指标**: 记录每个服务的处理时间
3. **错误追踪**: 详细的错误信息和堆栈
4. **审计日志**: 记录所有操作历史