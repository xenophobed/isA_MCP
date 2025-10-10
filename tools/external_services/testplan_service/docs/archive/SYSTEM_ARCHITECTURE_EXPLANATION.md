# 测试计划生成系统架构说明

## 核心概念关系图

```
用户PICS (User Capabilities) 
    ↓
包含：A.4.1-1/1 (FDD支持), A.4.3-3/1 (Band 1支持) 等
    ↓
条件判断 (Conditions)
    ↓
测试选择 (Test Selection)
    ↓
频段扩展 (Band Expansion)
    ↓
最终测试计划 (5695行)
```

## 1. 数据文件说明

### 1.1 complete_test_mappings.json
**作用**: 映射36.521-2的测试ID到36.521-1的测试ID
```json
{
  "test_mappings": {
    "mappings": {
      "6.2A.1": "6.2.2",    // 36.521-2的6.2A.1对应36.521-1的6.2.2
      "6.2A.2": "6.2.2A.1", // 最大功率降低测试
      ...
    }
  }
}
```
**关系**: test_id (from -2) → test_id (from -1)

### 1.2 band_mappings.json
**作用**: 映射PICS ID到频段名称
```json
{
  "band_mappings": [
    {
      "pics_id": "A.4.3-3/1",   // PICS标识符
      "band_name": "eFDD1",      // 频段名称
      "band_number": "1",        // 频段号
      "type": "FDD"              // 频段类型
    },
    ...
  ],
  "supported_bands": ["eFDD1", "eFDD2", ...] // 用户支持的频段
}
```
**关系**: feature_id (PICS) → band_name → 用于测试扩展

### 1.3 target_exact_patterns.json
**作用**: 记录目标Excel中每个测试的精确模式
```json
{
  "6.2.2": {
    "bands": ["eFDD1", "eFDD13", ...],           // 该测试使用的频段
    "conditions": [["TH", "VH"], ["TL", "VL"]], // 温度/电压组合
    "row_count": 310                             // 总行数
  },
  ...
}
```
**关系**: test_id → bands × conditions = row_count

### 1.4 target_test_analysis.json
**作用**: 目标测试的统计分析
```json
{
  "unique_tests": ["6.2.2", "6.2.2A.1", ...],  // 所有唯一测试
  "test_distribution": {
    "6.2.2": 310,    // 每个测试的行数
    ...
  },
  "section_summary": {
    "6": {"count": 65, "rows": 4299},  // Section 6有65个测试，4299行
    ...
  }
}
```

## 2. 核心关系链

### 2.1 PICS → Feature → Condition → Test
```
A.4.1-1/1 (PICS: FDD支持)
    ↓
启用FDD相关条件 (C142: IF A.4.1-1/1 THEN R ELSE N/A)
    ↓
选择相关测试 (6.2A.1: FDD最大输出功率)
    ↓
映射到36.521-1 (6.2.2)
```

### 2.2 PICS → Band → Test Expansion
```
A.4.3-3/1 = True (支持Band 1)
    ↓
band_mappings: A.4.3-3/1 → eFDD1
    ↓
测试6.2.2需要在eFDD1上执行
    ↓
生成: 6.2.2 + eFDD1 + TH/VH = 1行
      6.2.2 + eFDD1 + TL/VL = 1行
      ...
```

## 3. 完整数据流

### Step 1: 用户PICS输入
- 从Interlab Excel读取用户设备能力
- 例: A.4.1-1/1=True (支持FDD)
- 例: A.4.3-3/1=True (支持Band 1)

### Step 2: 条件评估
- 使用PICS值评估条件
- C142: IF A.4.1-1/1 AND A.4.1-1/2 THEN R
- 结果: R(必需), M(强制), O(可选), N/A(不适用)

### Step 3: 测试选择
- 基于条件结果选择测试
- 6.2A.1: applicability_condition = C142
- 如果C142=R，则包含6.2A.1

### Step 4: 测试映射
- 36.521-2 → 36.521-1
- 6.2A.1 → 6.2.2

### Step 5: 频段扩展
- 每个测试 × 支持的频段 × 环境条件
- 6.2.2 × [eFDD1, eFDD2, ...] × [(TH,VH), (TL,VL), ...]

### Step 6: 生成最终测试计划
- 总计5695行测试用例

## 4. 频段类型说明

### 4.1 单载波频段 (Single Carrier)
- eFDD1, eFDD2, ... (FDD频段)
- eTDD34, eTDD38, ... (TDD频段)
- 对应PICS: A.4.3-3/x

### 4.2 载波聚合频段 (Carrier Aggregation)
- CA_3C: 3载波聚合，带内连续
- CA_1A-8A: 双载波聚合，带间
- CA_5B-66A-66A: 三载波聚合，混合
- 对应PICS: A.4.3-4/x (CA相关)

## 5. 测试生成公式

```
总行数 = Σ(每个适用测试 × 该测试支持的频段数 × 该测试的环境条件组合数)

例如:
测试6.2.2:
- 支持13个频段
- 4种环境条件组合 [(TH,VH), (TL,VL), (TL,VH), (TN,VN)]
- 某些组合可能有额外要求
- 总计: 310行
```

## 6. 关键问题

### 当前系统的限制:
1. **测试提取不完整**: 只从36.521-2提取了65个测试，缺少Section 8, 9
2. **频段支持不全**: 用户PICS只支持部分频段，特别是缺少CA频段
3. **映射不完整**: 36.521-2到36.521-1的映射需要更多数据

### 解决方案:
1. 从36.521-1直接提取测试定义
2. 从36.521-3补充额外测试
3. 完善CA频段的PICS映射
4. 建立完整的测试依赖关系图