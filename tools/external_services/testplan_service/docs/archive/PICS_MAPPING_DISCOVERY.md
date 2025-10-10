# PICS 映射关系发现报告

## 关键发现

### 1. 映射关系不是显式的

**问题**：3GPP文档中，测试用例和PICS的映射关系**不是显式声明的**。

**测试文档 (36.521-1)** 中的描述：
```
Test applicability: This test case applies to all types of E-UTRA Power Class 3 UE release 8 and forward.
```

**PICS文档 (36.521-2)** 中的定义：
```
A.4.3-3b/2 - UE Power Class 3
A.0/1 - UE Release 8
A.4.1-1/1 - E-UTRA FDD
```

### 2. 需要语义映射

测试用例使用**自然语言描述**适用条件，而不是直接引用PICS ID。需要建立语义映射：

| 测试描述 | 对应PICS |
|---------|----------|
| "Power Class 3" | A.4.3-3b/2 |
| "release 8 and forward" | A.0/1 或更高 |
| "E-UTRA FDD" | A.4.1-1/1 |
| "E-UTRA TDD" | A.4.1-1/2 |
| "Band 1" | 需要查找Band相关PICS |

### 3. 实际的映射逻辑

```python
def map_test_to_pics(test_applicability):
    """
    将测试适用性描述映射到PICS项
    """
    pics_requirements = []
    
    # Power Class映射
    if "Power Class 3" in test_applicability:
        pics_requirements.append("A.4.3-3b/2")
    elif "Power Class 1" in test_applicability:
        pics_requirements.append("A.4.3-3b/1")
    
    # Release映射
    if "release 8" in test_applicability:
        if "and forward" in test_applicability:
            # Release 8或更高版本
            pics_requirements.append("A.0/1+")  # 表示A.0/1或更高
        else:
            pics_requirements.append("A.0/1")
    
    # 模式映射
    if "E-UTRA" in test_applicability:
        if "FDD" in test_applicability:
            pics_requirements.append("A.4.1-1/1")
        elif "TDD" in test_applicability:
            pics_requirements.append("A.4.1-1/2")
    
    return pics_requirements
```

## 为什么文档中没有直接的映射？

### 1. 规范分离
- **-1文档**：定义测试过程和要求
- **-2文档**：定义PICS（实现能力声明）
- 两者由不同工作组维护，使用不同的标识体系

### 2. 灵活性考虑
- 测试条件用自然语言描述，更易理解
- PICS用结构化ID，便于自动化处理
- 允许测试条件的灵活组合

### 3. 历史原因
- 3GPP规范演进多年，格式已固定
- 不同版本间需要保持兼容性

## 解决方案

### 方案1：建立映射规则库
```json
{
  "mapping_rules": [
    {
      "pattern": "Power Class (\\d+)",
      "pics_template": "A.4.3-3b/{group1_mapping}",
      "mappings": {
        "1": "1",
        "2": "4", 
        "3": "2",
        "5": "3"
      }
    },
    {
      "pattern": "release (\\d+)",
      "pics_template": "A.0/{release_offset}",
      "offset_base": 8,
      "offset_formula": "release_num - 7"
    }
  ]
}
```

### 方案2：手动维护映射表
基于业务知识，手动建立常见映射：
```csv
test_condition,pics_id,description
Power Class 3,A.4.3-3b/2,UE Power Class 3
E-UTRA FDD,A.4.1-1/1,E-UTRA FDD support
Release 17,A.0/10,UE Release 17
```

### 方案3：AI辅助映射
使用LLM理解测试描述，自动匹配对应的PICS：
```python
prompt = f"""
测试条件：{test_applicability}
可用PICS：{pics_list}
请匹配测试条件需要的PICS项。
"""
```

## 实施建议

### 短期方案
1. **提取所有测试的applicability描述**
2. **提取所有PICS项的描述**
3. **建立关键词映射表**（Power Class, Release, FDD/TDD等）
4. **基于规则进行自动映射**

### 长期方案
1. **建立完整的映射数据库**
2. **使用机器学习优化映射准确性**
3. **与3GPP标准组织合作，推动显式映射**

## 验证方法

通过已知的Excel转换结果验证映射准确性：
- 输入：701个支持的PICS
- 输出：5697个测试用例
- 验证：检查生成的测试是否符合PICS条件