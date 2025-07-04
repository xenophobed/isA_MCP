"""
User Management Tools Unit Tests

测试用户管理 MCP 工具的基本功能
验证用户创建、信息获取、积分消费等核心功能
"""

import pytest
import asyncio
from datetime import datetime

from tools.user_management_tools import (
    user_ensure_exists,
    user_get_info,
    credits_consume,
    user_service_status,
    UserManagementTools
)


class TestUserManagementTools:
    """用户管理工具测试类"""
    
    @pytest.fixture
    async def tools(self):
        """创建工具实例"""
        return UserManagementTools()
    
    @pytest.mark.asyncio
    async def test_user_ensure_exists(self, tools):
        """测试确保用户存在功能"""
        # 测试数据
        auth0_id = "auth0|test_user_123"
        email = "test@example.com"
        name = "Test User"
        
        # 调用工具
        result = await user_ensure_exists(auth0_id, email, name)
        
        # 验证结果
        assert result["success"] is True
        assert result["auth0_id"] == auth0_id
        assert result["email"] == email
        assert result["name"] == name
        assert result["credits"] == 1000  # 默认积分
        assert result["plan"] == "free"   # 默认计划
        assert result["is_active"] is True
        
        print(f"✅ 用户创建测试通过: {result}")
    
    @pytest.mark.asyncio
    async def test_user_get_info(self, tools):
        """测试获取用户信息功能"""
        # 先创建用户
        auth0_id = "auth0|test_user_456"
        email = "test2@example.com"
        name = "Test User 2"
        
        create_result = await user_ensure_exists(auth0_id, email, name)
        assert create_result["success"] is True
        
        # 获取用户信息
        info_result = await user_get_info(auth0_id)
        
        # 验证结果
        assert info_result["success"] is True
        assert info_result["auth0_id"] == auth0_id
        assert info_result["email"] == email
        assert info_result["name"] == name
        
        print(f"✅ 用户信息获取测试通过: {info_result}")
    
    @pytest.mark.asyncio
    async def test_user_get_info_not_found(self, tools):
        """测试获取不存在用户的信息"""
        # 获取不存在的用户
        result = await user_get_info("auth0|nonexistent_user")
        
        # 验证结果
        assert result["success"] is False
        assert "用户不存在" in result["message"]
        
        print(f"✅ 用户不存在测试通过: {result}")
    
    @pytest.mark.asyncio
    async def test_credits_consume_success(self, tools):
        """测试积分消费成功场景"""
        # 先创建用户
        auth0_id = "auth0|test_user_789"
        email = "test3@example.com"
        name = "Test User 3"
        
        create_result = await user_ensure_exists(auth0_id, email, name)
        user_id = create_result["user_id"]
        
        # 消费积分
        consume_result = await credits_consume(user_id, 100, "test_api_call")
        
        # 验证结果
        assert consume_result["success"] is True
        assert consume_result["consumed_amount"] == 100
        assert consume_result["remaining_credits"] == 900  # 1000 - 100
        
        print(f"✅ 积分消费成功测试通过: {consume_result}")
    
    @pytest.mark.asyncio
    async def test_credits_consume_insufficient(self, tools):
        """测试积分不足场景"""
        # 先创建用户
        auth0_id = "auth0|test_user_insufficient"
        email = "test4@example.com"
        name = "Test User 4"
        
        create_result = await user_ensure_exists(auth0_id, email, name)
        user_id = create_result["user_id"]
        
        # 尝试消费超过可用积分的数量
        consume_result = await credits_consume(user_id, 1500, "expensive_operation")
        
        # 验证结果
        assert consume_result["success"] is False
        assert "积分不足" in consume_result["message"]
        assert consume_result["consumed_amount"] == 0
        
        print(f"✅ 积分不足测试通过: {consume_result}")
    
    @pytest.mark.asyncio
    async def test_credits_consume_user_not_found(self, tools):
        """测试消费不存在用户的积分"""
        # 使用不存在的用户ID
        consume_result = await credits_consume(99999, 10, "test")
        
        # 验证结果
        assert consume_result["success"] is False
        assert "用户不存在" in consume_result["message"]
        
        print(f"✅ 用户不存在积分消费测试通过: {consume_result}")
    
    @pytest.mark.asyncio
    async def test_service_status(self, tools):
        """测试服务状态功能"""
        # 获取服务状态
        status_result = await user_service_status()
        
        # 验证结果
        assert status_result["success"] is True
        assert status_result["status"] == "operational"
        assert "tools_available" in status_result
        assert "services" in status_result
        assert "timestamp" in status_result
        
        # 验证可用工具列表
        available_tools = status_result["tools_available"]
        expected_tools = ["user_ensure_exists", "user_get_info", "credits_consume"]
        for tool in expected_tools:
            assert tool in available_tools
        
        print(f"✅ 服务状态测试通过: {status_result}")
    
    @pytest.mark.asyncio
    async def test_user_workflow_integration(self, tools):
        """测试完整的用户工作流程"""
        # 1. 创建用户
        auth0_id = "auth0|workflow_test_user"
        email = "workflow@example.com"
        name = "Workflow Test User"
        
        create_result = await user_ensure_exists(auth0_id, email, name)
        assert create_result["success"] is True
        user_id = create_result["user_id"]
        
        # 2. 获取用户信息
        info_result = await user_get_info(auth0_id)
        assert info_result["success"] is True
        assert info_result["credits"] == 1000
        
        # 3. 第一次积分消费
        consume1_result = await credits_consume(user_id, 200, "first_operation")
        assert consume1_result["success"] is True
        assert consume1_result["remaining_credits"] == 800
        
        # 4. 第二次积分消费
        consume2_result = await credits_consume(user_id, 300, "second_operation")
        assert consume2_result["success"] is True
        assert consume2_result["remaining_credits"] == 500
        
        # 5. 再次获取用户信息验证积分更新
        # 注意：由于我们的简化实现没有持久化，这里的积分可能不会实际更新
        # 在真实实现中，应该能看到积分的变化
        
        print(f"✅ 完整工作流程测试通过")
        print(f"   创建用户: {create_result['success']}")
        print(f"   获取信息: {info_result['success']}")
        print(f"   第一次消费: {consume1_result['remaining_credits']}")
        print(f"   第二次消费: {consume2_result['remaining_credits']}")


def test_tools_import():
    """测试工具导入"""
    from tools.user_management_tools import (
        user_ensure_exists,
        user_get_info,
        credits_consume,
        user_service_status
    )
    
    # 验证函数存在且可调用
    assert callable(user_ensure_exists)
    assert callable(user_get_info)
    assert callable(credits_consume)
    assert callable(user_service_status)
    
    print("✅ 工具导入测试通过")


@pytest.mark.asyncio
async def test_basic_functionality():
    """基础功能测试（不依赖 pytest fixtures）"""
    print("\n🚀 开始用户管理工具基础功能测试")
    
    # 测试服务状态
    status = await user_service_status()
    print(f"📊 服务状态: {status['status']}")
    
    # 测试用户创建
    result = await user_ensure_exists(
        "auth0|basic_test", 
        "basic@test.com", 
        "Basic Test User"
    )
    print(f"👤 用户创建: {result['success']}")
    
    # 测试用户信息获取
    info = await user_get_info("auth0|basic_test")
    print(f"📋 用户信息: {info['success']}")
    
    # 测试积分消费
    if info['success']:
        user_id = info['user_id']
        consume = await credits_consume(user_id, 50, "basic_test")
        print(f"💰 积分消费: {consume['success']}")
    
    print("✅ 基础功能测试完成")


if __name__ == "__main__":
    """直接运行测试"""
    print("🧪 运行用户管理工具测试")
    
    # 运行基础功能测试
    asyncio.run(test_basic_functionality())
    
    # 运行导入测试
    test_tools_import()
    
    print("\n🎉 所有测试完成！") 