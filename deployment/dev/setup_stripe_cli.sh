#!/bin/bash

# Stripe CLI 设置脚本
# 用于本地开发环境的 Webhook 测试

echo "🔧 设置 Stripe CLI 本地测试环境..."

# 检查 Stripe CLI 是否已安装
if ! command -v stripe &> /dev/null; then
    echo "📦 安装 Stripe CLI..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        brew install stripe/stripe-cli/stripe
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        wget -O stripe_cli.tar.gz https://github.com/stripe/stripe-cli/releases/latest/download/stripe_1.19.4_linux_x86_64.tar.gz
        tar -xzf stripe_cli.tar.gz
        sudo mv stripe /usr/local/bin/
        rm stripe_cli.tar.gz
    else
        echo "❌ 不支持的操作系统，请手动安装 Stripe CLI"
        echo "访问: https://stripe.com/docs/stripe-cli"
        exit 1
    fi
fi

echo "🔑 登录 Stripe CLI..."
echo "请在浏览器中完成登录流程"
stripe login

echo "🔀 设置本地 Webhook 转发..."
echo "这将把 Stripe 事件转发到本地服务器"
echo "请保持此终端窗口打开"

# 启动转发，监听所有事件并转发到后端服务
# Stripe webhook 直接发送到后端服务
stripe listen --forward-to localhost:8100/api/v1/webhooks/stripe

echo "✅ Stripe CLI 设置完成！"
echo "Webhook secret 将显示在上方，请复制到 .env.user_service 文件中"