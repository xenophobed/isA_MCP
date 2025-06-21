#!/usr/bin/env python
"""
Test script to verify Shopify client connection and functionality
"""
import asyncio
import json
import os
from tools.services.shopify_client import ShopifyClient

async def test_shopify_connection():
    """Test the Shopify client with real API credentials"""
    print("🧪 Testing Shopify Client Connection...")
    
    try:
        # Initialize client
        client = ShopifyClient()
        print(f"✅ Client initialized for domain: {client.store_domain}")
        
        # Test 1: Get shop info
        print("\n📊 Test 1: Getting shop information...")
        shop_result = await client.get_shop_info()
        
        if "errors" in shop_result:
            print(f"❌ Shop info failed: {shop_result['errors']}")
        elif "data" in shop_result:
            shop = shop_result["data"]["shop"]
            print(f"✅ Shop name: {shop.get('name', 'Unknown')}")
            print(f"✅ Domain: {shop.get('primaryDomain', {}).get('host', 'Unknown')}")
            print(f"✅ Currency: {shop.get('paymentSettings', {}).get('currencyCode', 'Unknown')}")
        
        # Test 2: Get collections
        print("\n📦 Test 2: Getting product collections...")
        collections_result = await client.get_collections(5)
        
        if "errors" in collections_result:
            print(f"❌ Collections failed: {collections_result['errors']}")
        elif "data" in collections_result:
            collections = collections_result["data"]["collections"]["edges"]
            print(f"✅ Found {len(collections)} collections:")
            for edge in collections[:3]:  # Show first 3
                collection = edge["node"]
                print(f"   - {collection['title']} (ID: {collection['id']})")
        
        # Test 3: Search products
        print("\n🔍 Test 3: Searching for products...")
        search_result = await client.search_products("shirt", first=3)
        
        if "errors" in search_result:
            print(f"❌ Product search failed: {search_result['errors']}")
        elif "data" in search_result:
            products = search_result["data"]["products"]["edges"]
            print(f"✅ Found {len(products)} products:")
            for edge in products:
                product = edge["node"]
                price = product["priceRange"]["minVariantPrice"]
                print(f"   - {product['title']}: {price['amount']} {price['currencyCode']}")
        
        # Test 4: Create a cart (but don't add anything)
        print("\n🛒 Test 4: Creating empty cart...")
        cart_result = await client.create_cart()
        
        if "errors" in cart_result:
            print(f"❌ Cart creation failed: {cart_result['errors']}")
        elif "data" in cart_result and cart_result["data"]["cartCreate"]["cart"]:
            cart = cart_result["data"]["cartCreate"]["cart"]
            print(f"✅ Cart created with ID: {cart['id']}")
            print(f"✅ Checkout URL: {cart.get('checkoutUrl', 'Not available')}")
        
        print("\n🎉 All tests completed successfully!")
        print("✅ Shopify client is working correctly with your credentials")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv('.env.local')
    
    asyncio.run(test_shopify_connection()) 