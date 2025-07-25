#!/usr/bin/env python3
"""
Test User ID Consistency
测试用户ID一致性修复

验证修复后的系统是否正常工作
"""

import sys
import asyncio
import logging
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.user_id_utils import (
    UserIdValidator, 
    UserIdConverter, 
    validate_user_id, 
    normalize_user_id,
    safe_user_id
)

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_user_id_validation():
    """测试用户ID验证功能"""
    print("\n" + "="*50)
    print("Testing User ID Validation")
    print("="*50)
    
    test_cases = [
        # Valid cases
        {
            "id": "auth0|550e8400-e29b-41d4-a716-446655440000",
            "expected_valid": True,
            "expected_type": "auth0"
        },
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "expected_valid": True,
            "expected_type": "uuid"
        },
        {
            "id": "test-user-001",
            "expected_valid": True,
            "expected_type": "test"
        },
        {
            "id": "dev_user",
            "expected_valid": True,
            "expected_type": "dev"
        },
        # Invalid cases
        {
            "id": "",
            "expected_valid": False,
            "expected_type": None
        },
        {
            "id": None,
            "expected_valid": False,
            "expected_type": None
        },
        {
            "id": "invalid-format",
            "expected_valid": False,
            "expected_type": None
        },
        {
            "id": "a" * 300,  # Too long
            "expected_valid": False,
            "expected_type": None
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        try:
            result = validate_user_id(test_case["id"])
            
            # 检查验证结果
            if result.is_valid == test_case["expected_valid"]:
                if test_case["expected_valid"]:
                    # 对于有效的ID，检查类型
                    if result.id_type == test_case["expected_type"]:
                        print(f"✓ Test {i}: PASS - {test_case['id']!r} -> {result.id_type}")
                        passed += 1
                    else:
                        print(f"✗ Test {i}: FAIL - Expected type {test_case['expected_type']}, got {result.id_type}")
                        failed += 1
                else:
                    print(f"✓ Test {i}: PASS - Invalid ID correctly rejected: {test_case['id']!r}")
                    passed += 1
            else:
                print(f"✗ Test {i}: FAIL - Expected valid={test_case['expected_valid']}, got {result.is_valid}")
                if result.error_message:
                    print(f"    Error: {result.error_message}")
                failed += 1
                
        except Exception as e:
            print(f"✗ Test {i}: ERROR - {e}")
            failed += 1
    
    print(f"\nValidation Tests: {passed} passed, {failed} failed")
    return failed == 0


def test_user_id_normalization():
    """测试用户ID标准化功能"""
    print("\n" + "="*50)
    print("Testing User ID Normalization")
    print("="*50)
    
    test_cases = [
        {
            "input": "  auth0|550E8400-E29B-41D4-A716-446655440000  ",
            "expected": "auth0|550E8400-E29B-41D4-A716-446655440000"
        },
        {
            "input": "550E8400-E29B-41D4-A716-446655440000",
            "expected": "550e8400-e29b-41d4-a716-446655440000"
        },
        {
            "input": "  TEST-USER-001  ",
            "expected": "test-user-001"
        },
        {
            "input": "DEV_USER",
            "expected": "dev_user"
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        try:
            result = normalize_user_id(test_case["input"])
            
            if result == test_case["expected"]:
                print(f"✓ Test {i}: PASS - '{test_case['input']}' -> '{result}'")
                passed += 1
            else:
                print(f"✗ Test {i}: FAIL - Expected '{test_case['expected']}', got '{result}'")
                failed += 1
                
        except Exception as e:
            print(f"✗ Test {i}: ERROR - {e}")
            failed += 1
    
    print(f"\nNormalization Tests: {passed} passed, {failed} failed")
    return failed == 0


def test_user_id_conversion():
    """测试用户ID转换功能"""
    print("\n" + "="*50)
    print("Testing User ID Conversion")
    print("="*50)
    
    # 测试从Auth0 ID提取UUID
    auth0_id = "auth0|550e8400-e29b-41d4-a716-446655440000"
    expected_uuid = "550e8400-e29b-41d4-a716-446655440000"
    
    extracted_uuid = UserIdConverter.extract_uuid_from_auth0(auth0_id)
    
    if extracted_uuid == expected_uuid:
        print(f"✓ UUID Extraction: PASS - {auth0_id} -> {extracted_uuid}")
        uuid_test_passed = True
    else:
        print(f"✗ UUID Extraction: FAIL - Expected {expected_uuid}, got {extracted_uuid}")
        uuid_test_passed = False
    
    # 测试从UUID创建Auth0 ID
    uuid_str = "550e8400-e29b-41d4-a716-446655440000"
    expected_auth0 = "auth0|550e8400-e29b-41d4-a716-446655440000"
    
    created_auth0 = UserIdConverter.create_auth0_id_from_uuid(uuid_str)
    
    if created_auth0 == expected_auth0:
        print(f"✓ Auth0 Creation: PASS - {uuid_str} -> {created_auth0}")
        auth0_test_passed = True
    else:
        print(f"✗ Auth0 Creation: FAIL - Expected {expected_auth0}, got {created_auth0}")
        auth0_test_passed = False
    
    # 测试生成功能
    test_id = UserIdConverter.generate_test_user_id(123)
    if test_id == "test-user-123":
        print(f"✓ Test ID Generation: PASS - {test_id}")
        test_gen_passed = True
    else:
        print(f"✗ Test ID Generation: FAIL - Expected test-user-123, got {test_id}")
        test_gen_passed = False
    
    # 测试UUID生成
    generated_uuid = UserIdConverter.generate_uuid_user_id()
    uuid_validation = validate_user_id(generated_uuid)
    
    if uuid_validation.is_valid and uuid_validation.id_type == "uuid":
        print(f"✓ UUID Generation: PASS - Generated valid UUID: {generated_uuid}")
        uuid_gen_passed = True
    else:
        print(f"✗ UUID Generation: FAIL - Generated invalid UUID: {generated_uuid}")
        uuid_gen_passed = False
    
    return all([uuid_test_passed, auth0_test_passed, test_gen_passed, uuid_gen_passed])


def test_safe_user_id():
    """测试安全用户ID获取功能"""
    print("\n" + "="*50)
    print("Testing Safe User ID Function")
    print("="*50)
    
    test_cases = [
        {
            "input": "auth0|550e8400-e29b-41d4-a716-446655440000",
            "default": "anonymous",
            "expected": "auth0|550e8400-e29b-41d4-a716-446655440000"
        },
        {
            "input": None,
            "default": "anonymous",
            "expected": "anonymous"
        },
        {
            "input": "",
            "default": "guest",
            "expected": "guest"
        },
        {
            "input": "invalid-format",
            "default": "unknown",
            "expected": "unknown"
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        try:
            result = safe_user_id(test_case["input"], test_case["default"])
            
            if result == test_case["expected"]:
                print(f"✓ Test {i}: PASS - safe_user_id({test_case['input']!r}, {test_case['default']!r}) -> {result!r}")
                passed += 1
            else:
                print(f"✗ Test {i}: FAIL - Expected {test_case['expected']!r}, got {result!r}")
                failed += 1
                
        except Exception as e:
            print(f"✗ Test {i}: ERROR - {e}")
            failed += 1
    
    print(f"\nSafe User ID Tests: {passed} passed, {failed} failed")
    return failed == 0


async def test_model_validation():
    """测试模型验证功能"""
    print("\n" + "="*50)
    print("Testing Model Validation")
    print("="*50)
    
    try:
        # 导入用户模型
        import sys
        import importlib.util
        
        # 动态导入用户模型
        model_path = project_root / "tools" / "services" / "user_service" / "models.py"
        spec = importlib.util.spec_from_file_location("user_models", model_path)
        user_models = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(user_models)
        
        User = user_models.User
        
        # 测试有效的用户创建
        valid_user_data = {
            "user_id": "auth0|550e8400-e29b-41d4-a716-446655440000",
            "auth0_id": "auth0|550e8400-e29b-41d4-a716-446655440000",
            "email": "test@example.com",
            "name": "Test User"
        }
        
        try:
            user = User(**valid_user_data)
            print(f"✓ Valid User Creation: PASS - Created user with ID: {user.user_id}")
            valid_creation_passed = True
        except Exception as e:
            print(f"✗ Valid User Creation: FAIL - {e}")
            valid_creation_passed = False
        
        # 测试无效的用户ID
        invalid_user_data = {
            "user_id": "invalid-format",
            "email": "test@example.com",
            "name": "Test User"
        }
        
        try:
            user = User(**invalid_user_data)
            print(f"✗ Invalid User ID Rejection: FAIL - Should have rejected invalid user_id")
            invalid_rejection_passed = False
        except ValueError as e:
            if "Invalid user_id format" in str(e):
                print(f"✓ Invalid User ID Rejection: PASS - Correctly rejected invalid user_id")
                invalid_rejection_passed = True
            else:
                print(f"✗ Invalid User ID Rejection: FAIL - Wrong error message: {e}")
                invalid_rejection_passed = False
        except Exception as e:
            print(f"✗ Invalid User ID Rejection: ERROR - Unexpected error: {e}")
            invalid_rejection_passed = False
        
        return valid_creation_passed and invalid_rejection_passed
        
    except ImportError as e:
        print(f"✗ Model Import: FAIL - Could not import User model: {e}")
        return False


async def main():
    """主测试函数"""
    print("=" * 60)
    print("User ID Consistency Test Suite")
    print("=" * 60)
    
    test_results = []
    
    # 运行所有测试
    test_results.append(("User ID Validation", test_user_id_validation()))
    test_results.append(("User ID Normalization", test_user_id_normalization()))
    test_results.append(("User ID Conversion", test_user_id_conversion()))
    test_results.append(("Safe User ID", test_safe_user_id()))
    test_results.append(("Model Validation", await test_model_validation()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed_tests = 0
    total_tests = len(test_results)
    
    for test_name, passed in test_results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {test_name}")
        if passed:
            passed_tests += 1
    
    print(f"\nOverall Result: {passed_tests}/{total_tests} test suites passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! User ID consistency is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)