# Test Combination Generation Logic (测试组合生成逻辑)

## 概览 (Overview)

从提取的参数表到生成测试组合的完整流程：

```
输入(Input) → 计算逻辑(Logic) → 输出(Output)
参数表 + PICS + 测试用例 → 组合算法 → 具体测试实例
```

## 1. 输入 (Inputs)

### 1.1 参数配置表 (Parameter Tables) - 从文档提取
```json
{
  "table_id": "6.2.2.4.1-1",
  "parameters": {
    "Test Environment": ["Normal", "TL/VL", "TL/VH", "TH/VL", "TH/VH"],
    "Test Frequencies": ["Low", "Mid", "High"],
    "Channel Bandwidth": [5, 10, 15, 20],  // MHz
    "Modulation": ["QPSK", "16QAM", "64QAM"]
  }
}
```

### 1.2 客户PICS数据 (Customer PICS) - 从Excel提取
```json
{
  "project_id": "PROJ_001",
  "supported_bands": ["eFDD1", "eFDD3", "eTDD38", "CA_1A-3A"],
  "supported_bandwidths": {
    "eFDD1": [5, 10, 15, 20],
    "eFDD3": [5, 10, 15, 20],
    "eTDD38": [5, 10, 20]
  },
  "capabilities": {
    "max_mimo": "2x2",
    "max_modulation": "64QAM"
  }
}
```

### 1.3 测试用例 (Test Case) - 从规范提取
```json
{
  "test_id": "6.2.2",
  "test_name": "UE Maximum Output Power",
  "applicable_bands": ["condition: C02"],  // 需要PICS映射
  "parameter_table_ref": "6.2.2.4.1-1"
}
```

## 2. 计算逻辑 (Calculation Logic)

### Step 1: 参数矩阵构建
```python
def build_parameter_matrix(test_case, parameter_table, pics_data):
    """
    构建该测试用例的参数矩阵
    """
    matrix = {
        'bands': [],      # 从PICS确定支持的频段
        'environments': [], # 从参数表获取
        'frequencies': [],  # 从参数表获取
        'bandwidths': [],   # 从参数表获取，根据频段过滤
        'modulations': []   # 从参数表获取，根据能力过滤
    }
    
    # 1. 确定适用频段 (基于PICS)
    if test_case.supports_ca:
        matrix['bands'] = pics_data['supported_ca_bands']
    else:
        matrix['bands'] = pics_data['supported_single_bands']
    
    # 2. 从参数表获取测试环境
    matrix['environments'] = parameter_table['Test Environment']
    
    # 3. 获取频率点
    matrix['frequencies'] = parameter_table['Test Frequencies']
    
    # 4. 根据频段过滤带宽
    for band in matrix['bands']:
        band_bw = pics_data['supported_bandwidths'][band]
        table_bw = parameter_table['Channel Bandwidth']
        matrix['bandwidths'].extend(
            set(band_bw) & set(table_bw)  # 交集
        )
    
    # 5. 根据UE能力过滤调制方式
    max_mod_index = ["QPSK", "16QAM", "64QAM", "256QAM"].index(
        pics_data['capabilities']['max_modulation']
    )
    matrix['modulations'] = [
        mod for mod in parameter_table['Modulation']
        if ["QPSK", "16QAM", "64QAM", "256QAM"].index(mod) <= max_mod_index
    ]
    
    return matrix
```

### Step 2: 组合生成策略
```python
def generate_combinations(matrix, strategy="pairwise"):
    """
    根据策略生成测试组合
    """
    
    if strategy == "full":
        # 全组合 - 笛卡尔积
        # bands × environments × frequencies × bandwidths × modulations
        # 例如: 4×5×3×4×3 = 720种组合
        return itertools.product(
            matrix['bands'],
            matrix['environments'], 
            matrix['frequencies'],
            matrix['bandwidths'],
            matrix['modulations']
        )
    
    elif strategy == "pairwise":
        # 成对组合 - 任意两个参数的所有组合至少出现一次
        # 大幅减少测试数量 (从720减少到约50-100)
        return pairwise_combinations(matrix)
    
    elif strategy == "priority":
        # 优先级策略 - 基于3GPP规定
        critical_combos = []
        
        # 1. 必测组合 (Normal环境 + Mid频率)
        for band in matrix['bands']:
            for bw in matrix['bandwidths']:
                critical_combos.append({
                    'band': band,
                    'environment': 'Normal',
                    'frequency': 'Mid',
                    'bandwidth': bw,
                    'modulation': 'QPSK'  # 基础调制
                })
        
        # 2. 边界条件 (极端环境)
        for env in ['TL/VL', 'TH/VH']:
            critical_combos.append({
                'band': matrix['bands'][0],  # 主频段
                'environment': env,
                'frequency': 'Low',  # 或 'High'
                'bandwidth': max(matrix['bandwidths']),
                'modulation': matrix['modulations'][-1]  # 最高调制
            })
        
        return critical_combos
```

### Step 3: 约束验证
```python
def apply_constraints(combinations, constraints):
    """
    应用3GPP约束规则，过滤无效组合
    """
    valid_combos = []
    
    for combo in combinations:
        # 约束1: TDD频段不支持某些带宽
        if 'TDD' in combo['band'] and combo['bandwidth'] == 15:
            continue  # TDD不支持15MHz
        
        # 约束2: 高温环境下功率限制
        if combo['environment'] == 'TH/VH' and combo['modulation'] == '256QAM':
            continue  # 高温下不测256QAM
        
        # 约束3: CA组合的带宽限制
        if 'CA_' in combo['band']:
            total_bw = sum(parse_ca_bandwidths(combo['band']))
            if total_bw > 40:  # CA总带宽不超过40MHz
                continue
        
        # 约束4: 频段特定限制
        if combo['band'] == 'eTDD38' and combo['frequency'] == 'High':
            continue  # Band 38没有High频率点
        
        valid_combos.append(combo)
    
    return valid_combos
```

## 3. 输出 (Output)

### 3.1 生成的测试实例
```json
[
  {
    "instance_id": "6.2.2_001",
    "test_id": "6.2.2",
    "test_name": "UE Maximum Output Power",
    "parameters": {
      "band": "eFDD1",
      "environment": "Normal",
      "frequency": "Mid",
      "bandwidth": 20,
      "modulation": "QPSK"
    },
    "execution_order": 1,
    "priority": "Critical",
    "estimated_duration": 120  // seconds
  },
  {
    "instance_id": "6.2.2_002",
    "test_id": "6.2.2",
    "parameters": {
      "band": "eFDD1",
      "environment": "Normal",
      "frequency": "Low",
      "bandwidth": 10,
      "modulation": "16QAM"
    },
    "execution_order": 2,
    "priority": "High",
    "estimated_duration": 120
  },
  // ... 更多组合
]
```

### 3.2 统计信息
```json
{
  "total_combinations": 48,  // 生成的总组合数
  "by_band": {
    "eFDD1": 16,
    "eFDD3": 16,
    "eTDD38": 12,
    "CA_1A-3A": 4
  },
  "by_priority": {
    "Critical": 8,   // 必测
    "High": 20,      // 重要
    "Medium": 20     // 可选
  },
  "coverage": {
    "pairwise_coverage": "100%",  // 成对覆盖率
    "parameter_coverage": {
      "bands": "4/4 (100%)",
      "environments": "5/5 (100%)",
      "frequencies": "3/3 (100%)",
      "bandwidths": "4/4 (100%)",
      "modulations": "3/3 (100%)"
    }
  }
}
```

## 4. 完整示例 (Complete Example)

### 输入场景
- 测试用例: 6.2.2 (UE Maximum Output Power)
- 客户支持: eFDD1, eFDD3 (单载波), CA_1A-3A (载波聚合)
- 参数表: 5个环境 × 3个频率 × 4个带宽 × 3个调制

### 计算过程
```python
# Step 1: 理论组合数
theoretical = 2 bands × 5 envs × 3 freqs × 4 bws × 3 mods = 360

# Step 2: 应用PICS过滤
# - eFDD1支持所有带宽 [5,10,15,20]
# - eFDD3只支持 [5,10,20]
after_pics = 330  # 减少了30个组合

# Step 3: 应用成对测试算法
pairwise_result = 45  # 大幅减少

# Step 4: 应用约束
# - 移除无效的环境/调制组合
# - 移除频段不支持的配置
final_combinations = 38
```

### 输出结果
- **全覆盖模式**: 330个测试实例 (耗时约11小时)
- **成对测试模式**: 38个测试实例 (耗时约1.3小时)
- **优先级模式**: 12个关键测试实例 (耗时约24分钟)

## 5. 关键算法 - 成对测试 (Pairwise Testing)

```python
def pairwise_algorithm(parameters):
    """
    实现In-Parameter-Order (IPO)算法
    确保任意两个参数的所有值组合至少出现一次
    """
    # 1. 从最大的两个参数开始
    param_sizes = [(p, len(values)) for p, values in parameters.items()]
    param_sizes.sort(key=lambda x: x[1], reverse=True)
    
    # 2. 构建初始对
    largest = param_sizes[0][0]
    second = param_sizes[1][0]
    pairs = list(itertools.product(
        parameters[largest], 
        parameters[second]
    ))
    
    # 3. 逐步扩展覆盖其他参数
    test_cases = []
    for pair in pairs:
        test_case = {largest: pair[0], second: pair[1]}
        
        # 为其他参数选择值，优先选择未覆盖的组合
        for param, _ in param_sizes[2:]:
            test_case[param] = select_uncovered_value(
                param, test_case, coverage_matrix
            )
        
        test_cases.append(test_case)
    
    return test_cases
```

## 总结

**输入**:
1. 参数配置表 (从3GPP文档提取)
2. 客户PICS数据 (设备能力)
3. 测试用例定义

**计算逻辑**:
1. 构建参数矩阵
2. 生成组合 (全组合/成对/优先级)
3. 应用约束过滤
4. 排序和优先级分配

**输出**:
- 具体的测试实例列表
- 每个实例包含完整参数值
- 执行顺序和优先级
- 覆盖率统计

**优化**: 从理论360个组合减少到38个实际测试，减少89%工作量，同时保持高缺陷检出率。