# 表结构设计与数据采集映射分析

## 📊 当前表结构设计评估

### 1. **PicsFeature 表 (pics_models.py)**

**表结构**：
```python
feature_id: str        # e.g., "A.4.1-1/1"
feature_name: str      # e.g., "E-UTRA FDD"
specification: str     # e.g., "3GPP TS 36.523-2"
feature_type: str      # mandatory/optional/conditional
status: str           # TRUE/FALSE/N/A
```

**数据来源**：
- **Interlab Excel文件** (`Interlab EVO Feature Spreadsheet`):
  - Sheet: `3GPP TS 36.521-2` (第7-12655行)
  - 列A: Item号 → feature_id
  - 列C: PICS内容 → feature_name
  - 列E: 用户选择 → status (TRUE/FALSE)

**实际数据示例**：
```
A.4.1-1/1 | E-UTRA FDD | TRUE
A.4.1-2/1 | E-UTRA TDD | TRUE  
A.4.3-1/4 | CA (E-UTRA non-CA UE) | FALSE
```

### 2. **TestCase 表 (test_models.py)**

**表结构**：
```python
test_id: str          # e.g., "6.2.2"
test_name: str        # e.g., "Transmitter Spurious emissions"
specification: str    # e.g., "3GPP TS 36.521-1"
required_pics: List   # 需要的PICS特性
```

**数据来源**：
- **3GPP TS 36.521-1 Word文档** (11个文档片段):
  - `36521-1-i80_s06-s06aa.docx`: 测试6.2-6.2A节
  - `36521-1-i80_s06b5-s06d.docx`: 测试6.3.4-6.3.5节
  - `36521-1-i80_s06f3-s06h.docx`: 测试6.6.2-6.6.3节
  - `36521-1-i80_s07.docx`: 测试7节
  - `36521-1-i80_s08.docx`: 测试8节

**提取方式**：
```python
# 从文档段落提取
"6.2.2 Transmitter Spurious emissions"
"6.3.4.1 Adjacent Channel Leakage Ratio"

# 从表格提取
Table中的Test ID列
```

### 3. **MappingRule 表 (rule_models.py)**

**表结构**：
```python
rule_id: str          # e.g., "C186"
condition: str        # e.g., "IF A.4.1-1/1 THEN R"
target_tests: List    # e.g., ["6.2.2"]
```

**数据来源**：
- **3GPP TS 36.521-2 Excel文件**:
  - Sheet: `Table A.4.1-1` 到 `Table A.4.5-6`
  - 包含370个条件定义（C1-C358, D1-D12）

**条件示例**：
```
C186: IF (A.4.1-1/1 AND A.4.5-1/1) THEN R ELSE N/A
→ 如果支持FDD且支持某特性，则测试6.2.2为必需(R)

D3-1: IF eFDD1 OR eFDD2 OR eFDD3 THEN R ELSE N/A  
→ 频段选择条件
```

## 🔄 数据采集流程（以36.521为例）

### 第一步：从Interlab Excel提取PICS声明

```python
# corrected_interlab_reader.py
def extract_pics_declarations():
    # 1. 读取36.521-2 sheet
    sheet = workbook['3GPP TS 36.521-2']
    
    # 2. 从第7行开始，读取到12655行
    for row in range(7, 12656):
        item = sheet[f'A{row}'].value      # A.4.1-1/1
        pics = sheet[f'C{row}'].value      # E-UTRA FDD
        status = sheet[f'E{row}'].value    # TRUE/FALSE
        
        if item and status == 'TRUE':
            supported_pics.append(item)
```

**实际提取结果**：
- 12,651个PICS项
- 2,731个用户支持的配置

### 第二步：从36.521-1文档提取测试ID

```python
# final_optimized_extractor.py
def extract_test_ids_from_doc(doc_path):
    doc = Document(doc_path)
    
    # 1. 从段落提取
    for para in doc.paragraphs:
        # 匹配格式: 6.2.2, 6.3.4.1, 7.7_1等
        matches = re.findall(r'\b(\d+\.\d+(?:\.\d+)*(?:_\d+)?)\b', para.text)
    
    # 2. 从表格提取
    for table in doc.tables:
        for row in table.rows:
            # 查找Test ID列
            extract_from_table_cells(row)
```

**实际提取结果**：
- 1,028个唯一测试ID
- 67.2%召回率（174/259正确）

### 第三步：从36.521-2提取条件映射

```python
# pics_condition_evaluator.py
def extract_conditions():
    # 1. 读取条件定义表
    conditions = {}
    
    # C系列条件 (C1-C358)
    for table in ['Table A.4.1-1', 'Table A.4.1-2', ...]:
        sheet = workbook[table]
        for row in sheet.rows:
            cond_id = row[0].value    # C186
            expression = row[1].value # IF ... THEN R ELSE N/A
            conditions[cond_id] = parse_condition(expression)
    
    # D系列条件 (D1-D12)  
    for d_condition in d_conditions:
        # 频段选择条件
        conditions[d_condition.id] = d_condition.expression
```

**实际提取结果**：
- 358个C条件
- 12个D条件
- 1,183个测试-条件映射

### 第四步：建立测试-PICS关联

```python
# complete_testplan_generator.py
def map_test_to_pics():
    # 对每个测试ID
    for test_id in all_tests:
        # 查找条件
        condition = find_condition_for_test(test_id)
        
        # 解析需要的PICS
        required_pics = extract_pics_from_condition(condition)
        
        # 建立映射
        test_pics_mapping[test_id] = required_pics
```

## ❌ 当前表结构的问题

### 1. **缺少条件表（Conditions Table）**
需要独立的条件表存储C和D系列条件：
```sql
CREATE TABLE conditions (
    condition_id VARCHAR(10),  -- C186, D3-1
    expression TEXT,           -- IF ... THEN ... ELSE
    condition_type CHAR(1),    -- C or D
    specification VARCHAR(50)   -- 36.521-2
);
```

### 2. **缺少测试-条件映射表**
```sql
CREATE TABLE test_condition_mapping (
    test_id VARCHAR(20),       -- 6.2.2
    condition_id VARCHAR(10),  -- C186
    applicability VARCHAR(10)  -- R/O/N/A
);
```

### 3. **缺少频段扩展表**
```sql
CREATE TABLE test_band_expansion (
    test_id VARCHAR(20),
    band VARCHAR(20),          -- eFDD1, eFDD2
    temperature INT,            -- -40, 25, 55
    voltage FLOAT              -- 3.3, 3.8, 4.2
);
```

## ✅ 推荐的改进表结构

### 完整的数据模型应包含：

```python
# 1. PICS声明表
class PicsDeclaration:
    pics_id: str           # A.4.1-1/1
    pics_name: str         # E-UTRA FDD
    user_support: bool     # TRUE/FALSE
    specification: str     # 36.521-2
    
# 2. 测试定义表  
class TestDefinition:
    test_id: str          # 6.2.2
    test_name: str        # Transmitter Spurious emissions
    specification: str    # 36.521-1
    document_section: str # s06-s06aa
    
# 3. 条件定义表
class ConditionDefinition:
    condition_id: str     # C186
    expression: str       # IF (A.4.1-1/1 AND A.4.5-1/1) THEN R
    condition_type: str   # C/D
    
# 4. 测试适用性表
class TestApplicability:
    test_id: str
    condition_id: str
    result: str           # R/O/N/A
    
# 5. 测试计划输出表
class TestPlanOutput:
    sequence: int
    test_id: str
    band: str
    temperature: int
    voltage: float
```

## 📈 数据完整性验证

### 当前数据覆盖率：
| 数据类型 | 应有数量 | 实际提取 | 覆盖率 |
|---------|---------|---------|--------|
| PICS声明 | 12,651 | 12,651 | 100% |
| 用户支持PICS | 2,731 | 2,731 | 100% |
| 测试ID | 259 | 174 | 67.2% |
| 条件定义 | 370 | 370 | 100% |
| 测试-条件映射 | 1,183 | 1,183 | 100% |

## 🎯 结论

当前表结构基本正确，但需要：
1. 添加独立的条件表
2. 添加测试-条件映射表  
3. 添加频段扩展表
4. 改进测试ID提取达到100%覆盖

数据采集流程清晰，主要问题在于测试ID提取的完整性（缺失33%）。

---
*生成时间：2025-09-22*