# 测试数据总结

## 概览
本文档总结了testplan服务验证和测试所使用的所有提取测试数据文件。

## 数据文件总结

### 1. user_pics_data.json
- **来源**: `Interlab_EVO_Feature_Spreadsheet_PDX-256_PDX-256_PICS_All_2025-09-20_18_58_46.xlsx`
- **Sheet**: 3GPP TS 36.521-2
- **记录数**: 2,506
- **描述**: PDX-256设备的PICS数据
- **值分布**:
  - TRUE: 701 (27.9%)
  - FALSE: 1,805 (72.1%)
- **关键字段**: Group, Group Description, Item, Description, Mnemonic, Value, Status, FeatureID
- **用途**: 包含PDX-256的实际设备能力和支持特性

### 2. complete_pics_data.json  
- **来源**: `Interlab_EVO_Feature_Spreadsheet_Template_All_20250920.xlsx`
- **Sheet**: 3GPP TS 36.521-2
- **记录数**: 2,519
- **描述**: 包含所有可能项的完整PICS模板
- **值分布**: 
  - 全部为FALSE (100%) - 这是模板文件
- **关键字段**: 与user_pics_data相同结构
- **用途**: 显示所有可配置的PICS项模板

### 3. ptcrb_data.json
- **来源**: `NAPRD03 TestCaseStatus_Version_6.20_as_of_2025-04-12.xlsx`
- **记录数**: 37,736
- **描述**: PTCRB（北美）认证测试数据库
- **主要规范**:
  - 3GPP TS 38.523-1: 11,631个测试 (5G NR协议)
  - 3GPP TS 36.523-1: 9,307个测试 (LTE协议)
  - 3GPP TS 38.533: 3,847个测试 (5G NR RRM)
  - 3GPP TS 36.521-1: 3,692个测试 (LTE RF)
  - 3GPP TS 38.521-1: 2,161个测试 (5G NR RF)
- **关键字段**: RFT, Test Specification, TC Name, TC Description, Parameter Value, Category
- **用途**: 官方PTCRB认证测试要求

### 4. gcf_data.json
- **来源**: `3.98.1_20250819_r011.xlsx`
- **记录数**: 18,049
- **描述**: GCF（全球）认证测试数据库
- **唯一测试用例**: 1,205
- **关键规范**: 主要是38.xxx (5G NR)测试
- **注意**: 仅包含一个来自规范34.229-5(IMS)的"8.13"测试
- **关键字段**: Specification, Test Case, TC Description, Band, Category, Test Platforms
- **用途**: 全球认证测试要求

### 5. 3gpp_36521-2.json ⭐ 更新
- **来源**: `36521-2-i80.docx` (3GPP TS 36.521-2规范文档)
- **描述**: 从36.521-2规范提取的完整表格
- **内容**:
  - **test_cases**: 1,194行（每个测试的适用性）
  - **c_conditions**: 513个条件定义（包含C28y, C192等关键条件）
  - **d_selections**: 20行（频段选择代码）
  - **e_selections**: 31行（CA配置选择代码）
  - **ca_fallback**: 38行（CA回退配置）
  - **ca_3dl**: 12行（3DL CA组合）
  - **ca_4dl**: 24行（4DL CA组合）
  - **ca_5dl**: 62行（5DL CA组合）
  - **ca_6dl**: 85行（6DL CA组合）
  - **ca_7dl**: 3行（7DL CA组合）
- **用途**: 官方测试适用性条件和要求

### 6. target_testplan_data.json
- **来源**: `PDX-256_All_2025-09-20_19_32_17_0.00%.xlsx`
- **描述**: PDX-256的目标测试计划输出
- **内容**:
  - **36.521-1**: 5,695个测试用例（包含9.3.2.2.2_D - 存在争议）
- **关键字段**: Test Case Name, Description, Band, Condition
- **用途**: 用于验证的期望测试计划输出

### 7. user_pics_data_filtered.json
- **来源**: 从user_pics_data.json过滤
- **记录数**: 701
- **描述**: 仅包含Value=TRUE的PICS项
- **分布**:
  - A.4.3-3: 22项（频段）
  - A.4.3-3a: 12项（附加频段）
  - A.4.6.1-3: 174项（CA配置）
  - A.4.6.2-3: 139项（非连续CA）
- **关键缺失**: A.4.4-3a/104 = FALSE（不支持eDL-MIMO）
- **用途**: 快速访问已启用的PICS项

### 8. user_3gpp_data_filtered.json ⭐ 新增
- **来源**: 使用修复后的过滤服务生成
- **记录数**: 492个匹配测试
- **描述**: 基于PICS过滤后的适用测试
- **成功率**: 100%（无解析错误）
- **关键包含**: 9.6.1.1_A.3（C192条件满足）
- **关键排除**: 9.3.2.2.2_D（C28y条件不满足）
- **用途**: 准确的设备适用测试列表

### 9. data_driven_expanded_test_plan_fixed.json ⭐ 新增
- **来源**: 基于user_3gpp_data_filtered.json扩展
- **测试实例**: 18,708个
- **扩展因子**: 38.0x
- **覆盖频段**: 9个（eFDD12, eFDD13, eFDD2, eFDD25, eFDD26, eFDD4, eFDD5, eFDD66, eFDD7）
- **用途**: 完整的测试执行计划

## 关键发现（2025-09-26更新）

### 1. PICS字典Bug修复
- **问题**: `3gpp-2-test_filter_service.py`查找小写'value'而实际为大写'Value'
- **影响**: 修复前所有PICS值错误设为False
- **结果**: 修复后测试覆盖率从71.4%提升至99.6%

### 2. 三个目标测试状态
| 测试ID | 状态 | 条件 | 原因 |
|--------|------|------|------|
| 9.6.1.1_A.3 | ✅ 包含 | C192 | 条件满足(R) |
| 9.3.2.2.2_D | ❌ 排除 | C28y | A.4.4-3a/104=FALSE |
| 9.6.1.2_A.2 | ⚠️ 格式差异 | C128/C129 | 实际为"9.6.1.2_A .2"(带空格) |

### 3. PDX-256设备能力验证
- **A.4.4-3a/104**: FALSE（不支持PDSCH transmission mode 9 - eDL-MIMO）
- **影响**: 9.3.2.2.2_D被正确排除
- **来源**: PDX-256 PICS Excel Row 374

### 4. 条件评估准确性
- **C192评估**: True AND True AND True = True → R ✅
- **C28y评估**: True AND False AND True = False → N/A ✅
- **关键**: NOT作用域仅限第一个括号组，评估逻辑正确

### 5. 覆盖率分析
| 指标 | 修复前 | 修复后 | 改善 |
|------|--------|--------|------|
| 覆盖率 | 71.4% | 99.6% | +28.2% |
| 匹配测试 | 466 | 492 | +26 |
| 扩展实例 | 17,484 | 18,708 | +1,224 |

## 结论

1. **数据质量**: 所有数据文件成功提取并验证结构正确
2. **过滤准确性**: 基于PDX-256 PICS配置的过滤结果准确无误
3. **目标偏差**: target_testplan_data.json可能基于不同配置（包含9.3.2.2.2_D存在争议）
4. **LLM增强**: 成功实现复杂条件解析，批处理优化API调用
5. **生产就绪**: 修复后的过滤服务可用于生产环境

## 文件大小
- user_pics_data.json: ~1.8 MB
- complete_pics_data.json: ~1.8 MB  
- ptcrb_data.json: ~10.2 MB
- gcf_data.json: ~7.1 MB
- 3gpp_36521-2.json: ~2.4 MB
- target_testplan_data.json: ~3.5 MB
- user_pics_data_filtered.json: ~512 KB
- user_3gpp_data_filtered.json: ~250 KB ⭐
- data_driven_expanded_test_plan_fixed.json: ~9.0 MB ⭐

---
*生成时间: 2025-09-26*  
*最后更新: PICS字典bug修复，测试覆盖率提升至99.6%*