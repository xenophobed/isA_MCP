# PICS to Test Plan 转换数据需求

## 核心问题
如何从 **PICS Excel** (用户支持的功能) 转换到 **Test Plan Excel** (需要执行的测试)?

## 转换逻辑

```
输入: PICS Excel → 筛选规则 → 输出: Test Plan Excel
                      ↑
                  需要的数据库
```

## 必须提取的数据

### 1. 测试用例数据 (从 36.521-1, 36.523-1 等文档)

每个测试用例必须包含：

| 字段 | 示例 | 说明 |
|-----|------|------|
| test_id | `7.1.1.1.1` | 测试用例唯一标识符 |
| test_name | `FDD/ Spurious Emissions test` | 测试用例名称 |
| specification | `36.521-1` | 所属规范 |
| required_pics | `["A.4.1-1/1", "A.4.3/4"]` | 必需的 PICS 项 |
| optional_pics | `["PC_xxx"]` | 可选的 PICS 项 |
| test_purpose | `Verify spurious emissions...` | 测试目的 |
| applicable_bands | `["Band 1", "Band 3"]` | 适用频段 |
| ue_categories | `["Cat-M1", "Cat-NB1"]` | UE 类别 |

### 2. PICS 定义数据 (从 36.521-2, 36.523-2 等文档)

每个 PICS 项必须包含：

| 字段 | 示例 | 说明 |
|-----|------|------|
| pics_id | `A.4.1-1/1` | PICS 唯一标识符 |
| pics_name | `FDD operation` | PICS 名称 |
| specification | `36.521-2` | 所属规范 |
| category | `RF` | 类别 (RF/RRM/Protocol) |
| mandatory | `true` | 是否必需 |
| description | `Support for FDD mode` | 描述 |

### 3. PICS 到测试用例的映射关系

| PICS ID | 适用的测试用例 | 条件 |
|---------|---------------|------|
| A.4.1-1/1 | 7.1.1.1.1, 7.1.2.1, 7.2.1.1 | REQUIRED |
| A.4.3/4 | 7.1.1.1.1, 8.1.1.1 | OPTIONAL |
| PC_xxx | 9.1.1.1 | REQUIRED |

## 筛选规则

```python
def filter_test_cases(pics_input, test_database):
    """
    根据用户支持的 PICS 筛选适用的测试用例
    """
    supported_pics = get_supported_pics(pics_input)  # TRUE 的 PICS
    applicable_tests = []
    
    for test in test_database:
        # 检查所有必需的 PICS 是否都被支持
        if all(pics in supported_pics for pics in test.required_pics):
            applicable_tests.append(test)
    
    return applicable_tests
```

## 具体示例

### 输入 (PICS Excel)
```
PICS_ID         | SupportedStartValue
A.4.1-1/1      | TRUE
A.4.3/4        | TRUE  
A.4.5-1        | FALSE
```

### 数据库查询
```sql
-- 找出需要 A.4.1-1/1 和 A.4.3/4 的测试
SELECT test_id, test_name 
FROM test_cases 
WHERE 'A.4.1-1/1' IN required_pics 
  AND 'A.4.3/4' IN required_pics
  AND 'A.4.5-1' NOT IN required_pics  -- 不支持的 PICS
```

### 输出 (Test Plan Excel)
```
Test_ID      | Test_Name                    | Specification | Required_PICS
7.1.1.1.1   | FDD/ Spurious Emissions test | 36.521-1     | A.4.1-1/1, A.4.3/4
7.1.2.1     | FDD/ Adjacent Channel test   | 36.521-1     | A.4.1-1/1
```

## 文档中的位置

### 测试用例位置 (在 -1 文档中)
- 章节标题: `7.1.1.1.1 Test case name`
- PICS 要求: 在 "PICS Selection", "Applicability", "Pre-test conditions" 部分
- 测试目的: 在 "Test Purpose (TP)" 部分

### PICS 定义位置 (在 -2 文档中)
- 附录 A: PICS proforma
- 格式: `A.4.1-1/1 Item description`
- 表格形式列出

## 关键挑战

1. **文档解析**: 测试用例分散在多个章节
2. **格式多样**: PICS 引用格式不一致
3. **映射关系**: 需要从文本中推断 PICS 和测试的关系
4. **数据量大**: 每个规范有数百到上千个测试用例

## 解决方案

1. **分段处理**: 按章节提取，保持上下文
2. **多重提取**: 结合规则和 AI
3. **增量构建**: 逐步建立映射数据库
4. **验证机制**: 交叉验证提取结果