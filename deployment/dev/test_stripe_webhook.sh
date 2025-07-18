#!/bin/bash

# 测试完整的 Stripe Webhook 流程
# 使用 Stripe CLI 触发真实的 webhook 事件

echo "🧪 测试 Stripe Webhook 完整流程"
echo "=================================="

# 检查前端服务（用于用户界面）
echo "🔍 检查前端服务 (localhost:3000)..."
if curl -f http://localhost:3000 2>/dev/null | grep -q "iapro.ai"; then
    echo "✅ 前端服务正常（用户界面）"
else
    echo "⚠️  前端服务未运行，但不影响webhook测试"
fi

# 检查后端服务
echo "🔍 检查后端服务 (localhost:8100)..."
if curl -f http://localhost:8100/health 2>/dev/null | grep -q "healthy"; then
    echo "✅ 后端服务正常"
else
    echo "❌ 后端服务未运行"
    echo "请运行: ./deployment/scripts/start_dev.sh"
    exit 1
fi

# 检查 Stripe CLI
echo "🔍 检查 Stripe CLI..."
if ! command -v stripe &> /dev/null; then
    echo "❌ Stripe CLI 未安装"
    echo "安装命令: brew install stripe/stripe-cli/stripe"
    exit 1
fi

echo "✅ Stripe CLI 已安装"

# 检查 Stripe CLI 登录状态
if ! stripe config --list | grep -q "test_mode_api_key"; then
    echo "❌ Stripe CLI 未登录"
    echo "请运行: stripe login"
    exit 1
fi

echo "✅ Stripe CLI 已登录"

echo ""
echo "🚀 开始测试流程..."
echo "==================="

# 1. 测试 checkout.session.completed 事件
echo "1️⃣ 触发 checkout.session.completed 事件..."
echo "这将模拟用户完成订阅购买"

stripe trigger checkout.session.completed --override customer_email=test@example.com

echo ""
echo "⏳ 等待事件处理 (5秒)..."
sleep 5

# 2. 测试 customer.subscription.updated 事件
echo "2️⃣ 触发 customer.subscription.updated 事件..."
echo "这将模拟订阅状态更新"

stripe trigger customer.subscription.updated

echo ""
echo "⏳ 等待事件处理 (5秒)..."
sleep 5

# 3. 检查日志
echo "📋 检查处理日志..."
if [[ -f "logs/stripe_cli.log" ]]; then
    echo "=== Stripe CLI 日志 (最后10行) ==="
    tail -10 logs/stripe_cli.log
fi

if [[ -f "logs/user_service.log" ]]; then
    echo ""
    echo "=== User Service 日志 (最后10行) ==="
    tail -10 logs/user_service.log | grep -i webhook || echo "未找到 webhook 相关日志"
fi

echo ""
echo "✅ 测试完成！"
echo "=============="
echo "💡 提示："
echo "• 检查前端控制台是否有转发日志"
echo "• 检查后端日志是否有 webhook 处理记录"
echo "• 如果用户状态未更新，请检查 metadata 中的 auth0_user_id"