#!/usr/bin/env python3
"""
验证 Stripe 配置的脚本
检查价格 ID 是否存在并且配置正确
"""

import stripe
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv('.env.user_service')

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

def verify_price_ids():
    """验证配置的价格 ID"""
    pro_price_id = os.getenv('STRIPE_PRO_PRICE_ID')
    enterprise_price_id = os.getenv('STRIPE_ENTERPRISE_PRICE_ID')
    
    print("🔍 验证 Stripe 价格配置...")
    print(f"Pro Price ID: {pro_price_id}")
    print(f"Enterprise Price ID: {enterprise_price_id}")
    print("-" * 50)
    
    # 验证 Pro 价格
    try:
        pro_price = stripe.Price.retrieve(pro_price_id)
        print("✅ Pro 计划价格验证成功:")
        print(f"   - 名称: {pro_price.nickname or 'N/A'}")
        print(f"   - 金额: ${pro_price.unit_amount / 100}")
        print(f"   - 货币: {pro_price.currency.upper()}")
        print(f"   - 间隔: {pro_price.recurring.interval if pro_price.recurring else 'one-time'}")
    except stripe.error.InvalidRequestError as e:
        print(f"❌ Pro 计划价格验证失败: {e}")
        return False
    
    # 验证 Enterprise 价格
    try:
        enterprise_price = stripe.Price.retrieve(enterprise_price_id)
        print("✅ Enterprise 计划价格验证成功:")
        print(f"   - 名称: {enterprise_price.nickname or 'N/A'}")
        print(f"   - 金额: ${enterprise_price.unit_amount / 100}")
        print(f"   - 货币: {enterprise_price.currency.upper()}")
        print(f"   - 间隔: {enterprise_price.recurring.interval if enterprise_price.recurring else 'one-time'}")
    except stripe.error.InvalidRequestError as e:
        print(f"❌ Enterprise 计划价格验证失败: {e}")
        return False
    
    print("\n🎉 所有价格配置验证成功！")
    return True

def create_missing_prices():
    """创建缺失的价格（如果需要）"""
    print("🛠️  创建测试价格...")
    
    try:
        # 创建 Pro 产品和价格
        pro_product = stripe.Product.create(
            name="Pro Plan",
            description="Advanced AI features with 10,000 credits"
        )
        
        pro_price = stripe.Price.create(
            unit_amount=2000,  # $20.00
            currency='usd',
            recurring={'interval': 'month'},
            product=pro_product.id,
            nickname="Pro Monthly"
        )
        
        print(f"✅ Pro 价格创建成功: {pro_price.id}")
        
        # 创建 Enterprise 产品和价格
        enterprise_product = stripe.Product.create(
            name="Enterprise Plan",
            description="Premium AI features with 50,000 credits"
        )
        
        enterprise_price = stripe.Price.create(
            unit_amount=10000,  # $100.00
            currency='usd',
            recurring={'interval': 'month'},
            product=enterprise_product.id,
            nickname="Enterprise Monthly"
        )
        
        print(f"✅ Enterprise 价格创建成功: {enterprise_price.id}")
        
        print("\n📝 请更新配置文件中的价格 ID:")
        print(f"STRIPE_PRO_PRICE_ID={pro_price.id}")
        print(f"STRIPE_ENTERPRISE_PRICE_ID={enterprise_price.id}")
        
    except Exception as e:
        print(f"❌ 创建价格失败: {e}")

if __name__ == "__main__":
    if not stripe.api_key:
        print("❌ 请设置 STRIPE_SECRET_KEY 环境变量")
        exit(1)
    
    success = verify_price_ids()
    
    if not success:
        create_new = input("\n❓ 是否创建新的测试价格? (y/n): ")
        if create_new.lower() == 'y':
            create_missing_prices()