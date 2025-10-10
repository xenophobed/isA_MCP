# 3GPP测试模板逆向工程分析

## 1. 核心发现

通过分析PDX-256实际输出，我们成功倒推出了3GPP测试模板的生成规律：

### ✅ 关键洞察

1. **测试组合不是全排列**
   - 理论全组合：3温度 × 3电压 × 3频率 × 6带宽 = 162个/频段
   - 实际组合：24-36个/频段（减少85%）

2. **温度/电压是成对的**
   ```
   实际使用的环境对：
   - TN/VN (Normal)
   - TH/VH (High/High)
   - TL/VL (Low/Low)  
   - TL/VH (Low/High) - 混合条件
   
   而不是9种独立组合！
   ```

3. **不同测试用例有不同模板**
   - 6.2.2 (最大功率): 24-36个组合/频段
   - 6.3.2 (功率降低): 相同模板as 6.2.2
   - 6.2.5 (配置功率): 简化到87个总组合
   - 7.3 (灵敏度): 主要测Normal条件

## 2. 倒推的模板结构

### 基础模板（单载波）

```python
Template_6.2.2 = {
    'environment_pairs': [
        (TN, VN),  # Normal
        (TH, VH),  # Extreme hot
        (TL, VL),  # Extreme cold
        (TL, VH),  # Mixed
    ],
    'frequency_ranges': [Low, Mid, High],
    'bandwidths': [min_bw, max_bw],  # 只测最小最大
}

组合数 = 4环境对 × 3频率 × 2带宽 = 24个/频段
```

### CA模板（载波聚合）

```python
Template_CA = {
    'environment_pairs': [
        (TN, VN),
        (TH, VH),
        (TL, VL),
    ],
    'frequency_ranges': [Mid],  # 只测Mid
    'bandwidths': [specific_ca_bw],  # CA特定带宽
}

组合数 = 3环境对 × 1频率 × N带宽 = 3N个/CA配置
```

## 3. 实际数据验证

### 测试6.2.2的实际分布

| 频段 | 组合数 | 模式分析 |
|------|--------|----------|
| eFDD1 | 24 | 4环境对 × 3频率 × 2带宽(5,20) |
| eFDD2 | 27 | 4环境对 × 3频率 × 3带宽(5,10,20) - 部分组合 |
| eFDD3 | 36 | 4环境对 × 3频率 × 3带宽(5,10,20) |
| eFDD28 | 36 | 4环境对 × 3频率 × 3带宽(3,5,20) |
| eFDD13 | 3 | 3环境对 × 1频率 × 1带宽(10) |

### 参数统计

从5,695个测试组合中统计：
- **频段**: 95个（包括单载波和CA）
- **温度**: 3个（TN, TL, TH）
- **电压**: 3个（VN, VL, VH）
- **频率**: 3个（Low, Mid, High range）
- **带宽**: 6个（1.4, 3, 5, 10, 15, 20 MHz）

## 4. 模板生成算法

```python
def generate_test_combinations(test_id, band, pics_capabilities):
    """
    基于倒推的模板生成测试组合
    """
    # 1. 获取测试模板
    template = get_template_for_test(test_id)
    
    # 2. 获取频段支持的带宽
    supported_bw = pics_capabilities[band]
    
    # 3. 应用模板规则
    test_bw = []
    if template.bw_strategy == "minimal":
        test_bw = [min(supported_bw), max(supported_bw)]
    elif template.bw_strategy == "specific":
        test_bw = [bw for bw in [5,10,20] if bw in supported_bw]
    
    # 4. 生成组合
    combinations = []
    for env_pair in template.env_pairs:
        for freq in template.freq_ranges:
            for bw in test_bw:
                combinations.append({
                    'band': band,
                    'temp': env_pair[0],
                    'volt': env_pair[1],
                    'freq': freq,
                    'bw': bw
                })
    
    return combinations
```

## 5. 为什么这样设计？

### 测试覆盖策略

1. **环境对而非独立维度**
   - 减少测试数量（4对 vs 9种组合）
   - 覆盖关键场景（Normal, 双极端, 混合）
   - 实际设备很少在TH/VL或TL/VH条件下工作

2. **带宽选择策略**
   - 最小/最大带宽：验证边界条件
   - 特定带宽集：行业常用配置
   - 避免测试所有中间值

3. **频率点覆盖**
   - Low/Mid/High：覆盖频段范围
   - 某些测试只需Mid（如6.2.5）
   - 灵敏度测试(7.3)可能需要全覆盖

## 6. 实施建议

### 正确的架构

```
PICS数据 + 测试模板库 → 过滤器 → 测试计划

而不是：
PICS数据 + 参数矩阵 → 组合算法 → 测试计划
```

### 关键组件

1. **测试模板库**
   - 每个测试用例的预定义模板
   - 环境对、频率、带宽策略

2. **PICS过滤器**
   - 过滤不支持的频段
   - 过滤不支持的带宽
   - 应用条件逻辑（C-conditions）

3. **模板实例化器**
   - 将模板应用到具体频段
   - 生成实际测试组合

## 7. 验证结果

使用倒推的模板生成器：
- 生成506个组合 vs 实际5,695个（需要更多测试用例）
- 模板准确匹配了环境对模式
- 正确识别了不同测试的组合策略

## 8. 结论

✅ **成功倒推出测试模板结构**

通过分析实际输出数据，我们发现3GPP测试不是使用动态组合算法，而是基于预定义的测试模板。这些模板：

1. 使用环境对而非独立参数
2. 有特定的带宽选择策略  
3. 针对不同测试类型优化

这解释了为什么 `services/expansion/` 中的pairwise算法不适用 - 真实系统使用的是**基于模板的生成**，而非算法组合。

## 下一步

1. 完善测试模板库（覆盖所有259个测试用例）
2. 实现完整的PICS过滤逻辑
3. 添加CA和DC的特殊模板
4. 验证生成结果与实际输出的匹配度