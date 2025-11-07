# Test Data Summary

## Overview
This document summarizes all extracted test data files used for the testplan service validation and testing.

## Data Files Summary

### 1. user_pics_data.json
- **Source**: `Interlab_EVO_Feature_Spreadsheet_PDX-256_PDX-256_PICS_All_2025-09-20_18_58_46.xlsx`
- **Sheet**: 3GPP TS 36.521-2
- **Records**: 2,506
- **Description**: Actual device PICS (Protocol Implementation Conformance Statement) data
- **Value Distribution**:
  - TRUE: 701 (27.9%)
  - FALSE: 1,805 (72.1%)
- **Key Fields**: Group, Group Description, Item, Description, Mnemonic, Value, Status, FeatureID
- **Purpose**: Contains the actual device capabilities and supported features for PDX-256

### 2. complete_pics_data.json  
- **Source**: `Interlab_EVO_Feature_Spreadsheet_Template_All_20250920.xlsx`
- **Sheet**: 3GPP TS 36.521-2
- **Records**: 2,519
- **Description**: Complete PICS template with all possible items
- **Value Distribution**: 
  - All FALSE (100%) - This is a template file
- **Key Fields**: Same structure as user_pics_data
- **Purpose**: Template showing all possible PICS items that can be configured

### 3. ptcrb_data.json
- **Source**: `NAPRD03 TestCaseStatus_Version_6.20_as_of_2025-04-12.xlsx`
- **Records**: 37,736
- **Description**: PTCRB (North America) certification test database
- **Top Specifications**:
  - 3GPP TS 38.523-1: 11,631 tests (5G NR Protocol)
  - 3GPP TS 36.523-1: 9,307 tests (LTE Protocol)
  - 3GPP TS 38.533: 3,847 tests (5G NR RRM)
  - 3GPP TS 36.521-1: 3,692 tests (LTE RF)
  - 3GPP TS 38.521-1: 2,161 tests (5G NR RF)
- **Key Fields**: RFT, Test Specification, TC Name, TC Description, Parameter Value, Category
- **Purpose**: Official PTCRB certification test requirements

### 4. gcf_data.json
- **Source**: `3.98.1_20250819_r011.xlsx`
- **Records**: 18,049
- **Description**: GCF (Global) certification test database
- **Unique Test Cases**: 1,205
- **Key Specifications**: Primarily 38.xxx (5G NR) tests
- **Notable**: Contains only one "8.13" test from specification 34.229-5 (IMS)
- **Key Fields**: Specification, Test Case, TC Description, Band, Category, Test Platforms
- **Purpose**: Global certification test requirements

### 5. 3gpp_36521-2.json
- **Source**: `36521-2-i80.docx` (3GPP TS 36.521-2 specification document)
- **Description**: Complete tables extracted from 36.521-2 specification
- **Contents**:
  - **test_cases**: 1,420 rows (Applicability of each test)
  - **c_conditions**: 534 rows (Conditional requirements)
  - **d_selections**: 20 rows (Band selection codes)
  - **e_selections**: 31 rows (CA configuration selection codes)
  - **ca_fallback**: 38 rows (CA fallback configurations)
  - **ca_3dl**: 12 rows (3DL CA combinations)
  - **ca_4dl**: 24 rows (4DL CA combinations)
  - **ca_5dl**: 62 rows (5DL CA combinations)
  - **ca_6dl**: 85 rows (6DL CA combinations)
  - **ca_7dl**: 3 rows (7DL CA combinations)
  - **all_raw_tables**: 81 tables (complete document tables)
- **Purpose**: Official test applicability conditions and requirements

### 6. target_testplan_data.json
- **Source**: `PDX-256_All_2025-09-20_19_32_17_0.00%.xlsx`
- **Description**: Target test plan output from PDX-256
- **Contents**:
  - **3GPP TS 36.521-1**: 5,702 test cases (LTE RF conformance)
  - **3GPP TS 36.521-3**: 1,179 test cases (LTE RRM conformance)
- **Notable**: No 8.13.x tests present (0 found)
- **Key Fields**: Test ID, Description, Band, Status
- **Purpose**: Expected test plan output for validation

### 7. user_pics_data_filtered.json
- **Source**: Filtered from user_pics_data.json
- **Records**: 701
- **Description**: Only PICS items where Value=TRUE
- **Distribution by Prefix**:
  - A.4.3-3: 22 items (Bands)
  - A.4.3-3a: 12 items (Additional bands)
  - A.4.6.1-3: 174 items (CA configurations)
  - A.4.6.2-3: 139 items (Non-contiguous CA)
- **Purpose**: Quick access to active/enabled PICS items

## Key Findings

### 1. Test ID Mapping Challenge
- **36.521-2** defines 68 tests with ID pattern 8.13.x.x.x (MIMO tests)
- **PTCRB** has 0 tests with 8.13.x pattern in 36.521-1
- **GCF** has only 1 test "8.13" from different spec (34.229-5)
- **PDX-256 output** has 0 tests with 8.13.x pattern

### 2. PICS Evaluation
- User device declares support for:
  - 4Rx antenna ports (A.4.5-1/39: TRUE)
  - High UE categories (6, 9, 11)
  - Intra-band non-contiguous CA (A.4.6.2-1/1: TRUE)
- These capabilities trigger C254 condition → 8.13.x tests required
- But these tests don't exist in certification databases

### 3. Database Coverage
| Specification | PTCRB | GCF | PDX-256 Output |
|--------------|--------|-----|----------------|
| 36.521-1 (LTE RF) | 3,692 | 0 | 5,702 |
| 36.521-2 (LTE Applicability) | 0 | 0 | N/A |
| 36.521-3 (LTE RRM) | 0 | 0 | 1,179 |
| 36.523-1 (LTE Protocol) | 9,307 | 0 | 0 |
| 38.xxx (5G NR) | 17,639 | 18,049 | 0 |

### 4. Mapping Success Rate
- Filtered 36.521-2 test IDs: 302
- Successfully mapped to PTCRB TC Names: ~48%
- Found in PDX-256 output: ~43%
- Unmappable (not in any database): ~36%

## Conclusions

1. **Specification vs Certification Gap**: 36.521-2 defines tests that haven't been adopted by certification bodies
2. **Regional Differences**: PTCRB focuses on LTE/5G mix, GCF primarily on 5G NR
3. **Evolution Lag**: Advanced features (4x4 MIMO, high-order CA) defined in specs but not yet required for certification
4. **Data Quality**: All data files successfully extracted and validated with correct structure

## File Sizes
- user_pics_data.json: ~1.8 MB
- complete_pics_data.json: ~1.8 MB  
- ptcrb_data.json: ~10.2 MB
- gcf_data.json: ~7.1 MB
- 3gpp_36521-2.json: ~2.4 MB
- target_testplan_data.json: ~3.5 MB
- user_pics_data_filtered.json: ~512 KB

---
*Generated: 2024*
*Last Updated: Test data extraction completed successfully*
