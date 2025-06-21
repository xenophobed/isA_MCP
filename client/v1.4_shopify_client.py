#!/usr/bin/env python3
"""
Shopify MCP Client v1.4
Provides Shopify integration testing capabilities through MCP
"""

import os
import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

class ShopifyTestClient:
    """Shopify Test Client implementation"""
    
    def __init__(self, server_url: str = "http://localhost:8001/mcp"):
        self.server_url = server_url
        self.session = None
        self.client_context = None
        self.session_context = None
        # Get Shopify credentials from environment
        self.shop_url = os.getenv("SHOPIFY_SHOP_URL")
        self.access_token = os.getenv("SHOPIFY_ACCESS_TOKEN")
        
        # Connection URLs in priority order
        self.connection_urls = [
            "http://localhost:8001/mcp",   # Primary
            "http://localhost:8002/mcp",   # Backup 1
            "http://localhost:8003/mcp"    # Backup 2
        ]
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()
    
    async def connect(self):
        """Connect to MCP server with fallback support"""
        print("🔌 Connecting to Shopify server...")
        
        # Try each connection URL until one works
        for url in self.connection_urls:
            try:
                print(f"🔄 Attempting connection: {url}")
                
                # Create streamable HTTP client
                self.client_context = streamablehttp_client(url)
                self.read, self.write, _ = await self.client_context.__aenter__()
                
                # Create session
                self.session_context = ClientSession(self.read, self.write)
                self.session = await self.session_context.__aenter__()
                
                # Initialize session
                await self.session.initialize()
                print("✅ Shopify session initialized")
                return
                
            except Exception as e:
                print(f"❌ Connection failed for {url}: {e}")
                await self._cleanup_failed_connection()
                continue
        
        raise Exception("❌ All connection attempts failed")
    
    async def _cleanup_failed_connection(self):
        """Clean up failed connection attempts"""
        try:
            if self.session_context:
                await self.session_context.__aexit__(None, None, None)
            if self.client_context:
                await self.client_context.__aexit__(None, None, None)
        except:
            pass
        finally:
            self.session = None
            self.session_context = None
            self.client_context = None
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            if self.session_context:
                await self.session_context.__aexit__(None, None, None)
            if self.client_context:
                await self.client_context.__aexit__(None, None, None)
            print("🧹 Cleanup completed")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
    
    async def call_tool(self, name: str, arguments: Dict) -> Dict:
        """Call an MCP tool and return the result"""
        if not self.session:
            return {"error": "No session available"}
        
        try:
            print(f"🔧 Calling tool: {name}")
            result = await self.session.call_tool(name, arguments)
            
            if hasattr(result, 'content') and result.content:
                content_item = result.content[0]
                # Convert any content type to string first
                content_str = str(content_item)
                try:
                    return json.loads(content_str)
                except json.JSONDecodeError:
                    return {"error": f"Invalid JSON response: {content_str}"}
            return {"error": "No content in response"}
            
        except Exception as e:
            print(f"❌ Tool call failed: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return {"error": str(e)}
    
    # === Test Operations ===
    
    async def test_shop_info(self) -> Dict:
        """Test getting shop information"""
        return await self.call_tool("shopify_get_shop_info", {
            "user_id": "test_user"
        })
    
    async def test_search_products(self, query: str = "electronics", min_inventory: int = 1) -> Dict:
        """Test searching for products with inventory"""
        return await self.call_tool("shopify_search_products", {
            "query": query,
            "first": 5,
            "user_id": "test_user"
        })
    
    async def test_get_product(self, product_id: str) -> Dict:
        """Test getting product details"""
        return await self.call_tool("shopify_get_product_details", {
            "product_id": product_id,
            "user_id": "test_user"
        })
    
    async def test_create_cart(self) -> Dict:
        """Test creating a new cart"""
        return await self.call_tool("shopify_create_cart", {
            "user_id": "test_user"
        })
    
    async def test_add_to_cart(self, cart_id: str, variant_id: str, quantity: int = 1) -> Dict:
        """Test adding item to cart"""
        return await self.call_tool("shopify_add_to_cart", {
            "cart_id": cart_id,
            "variant_id": variant_id,
            "quantity": quantity,
            "user_id": "test_user"
        })
    
    async def test_get_cart(self, cart_id: str) -> Dict:
        """Test getting cart contents"""
        return await self.call_tool("shopify_get_cart", {
            "cart_id": cart_id,
            "user_id": "test_user"
        })
    
    async def test_start_checkout(self, cart_id: str) -> Dict:
        """Test starting checkout process"""
        return await self.call_tool("shopify_checkout", {
            "cart_id": cart_id,
            "user_id": "test_user"
        })
    
    async def test_add_shipping_address(self, checkout_id: str, address: Dict) -> Dict:
        """Test adding shipping address"""
        return await self.call_tool("shopify_add_shipping_address", {
            "checkout_id": checkout_id,
            "address": address,
            "user_id": "test_user"
        })
    
    async def test_get_shipping_rates(self, checkout_id: str) -> Dict:
        """Test getting available shipping rates"""
        return await self.call_tool("shopify_get_shipping_rates", {
            "checkout_id": checkout_id,
            "user_id": "test_user"
        })
    
    async def test_select_shipping_rate(self, checkout_id: str, rate_handle: str) -> Dict:
        """Test selecting shipping rate"""
        return await self.call_tool("shopify_select_shipping_rate", {
            "checkout_id": checkout_id,
            "rate_handle": rate_handle,
            "user_id": "test_user"
        })
    
    async def test_add_payment(self, checkout_id: str, payment_info: Dict) -> Dict:
        """Test adding payment information"""
        return await self.call_tool("shopify_add_payment", {
            "checkout_id": checkout_id,
            "payment_info": payment_info,
            "user_id": "test_user"
        })
    
    async def test_complete_order(self, checkout_id: str) -> Dict:
        """Test completing the order"""
        return await self.call_tool("shopify_complete_order", {
            "checkout_id": checkout_id,
            "user_id": "test_user"
        })

async def main():
    """主测试函数"""
    print("🧪 Shopify Shopping Flow Test Client")
    print("=" * 50)
    
    async with ShopifyTestClient() as client:
        # Test 1: Shop info
        shop_info = await client.test_shop_info()
        if "error" in shop_info:
            print(f"❌ Shop info test failed: {shop_info['error']}")
            return
        
        print("\n" + "-" * 50)
        
        # Test 2: Search products
        products = await client.test_search_products("electronics")
        if "error" in products:
            print(f"❌ Product search failed: {products['error']}")
            return
        
        print("\n" + "-" * 50)
        
        # Test 3: Get product details for first product
        if products and "products" in products:
            first_product = products["products"][0]
            product_details = await client.test_get_product(first_product["id"])
            if "error" in product_details:
                print(f"❌ Failed to get product details: {product_details['error']}")
            else:
                print(f"✅ Product: {product_details['title']}")
                print(f"   Description: {product_details['description'][:100]}...")
                print(f"   Available: {product_details['available']}")
                print(f"   Variants: {len(product_details['variants'])}")
        
        print("\n" + "-" * 50)
        
        # Test 4: Add to cart
        if products and "products" in products and products["products"]:
            first_product = products["products"][0]
            if first_product["available"] and first_product["variant_id"]:
                cart = await client.test_create_cart()
                if "error" in cart:
                    print(f"❌ Failed to create cart: {cart['error']}")
                else:
                    add_to_cart_result = await client.test_add_to_cart(cart["id"], first_product["variant_id"], 1)
                    if "error" in add_to_cart_result:
                        print(f"❌ Failed to add to cart: {add_to_cart_result['error']}")
                    else:
                        print(f"✅ Added to cart: {add_to_cart_result['message']}")
                        print(f"   Cart total: {add_to_cart_result['total_amount']} {add_to_cart_result['currency']}")
                        print(f"   Total items: {add_to_cart_result['total_quantity']}")
            
            print("\n" + "-" * 50)
            
            # Test 5: Get cart
            cart_contents = await client.test_get_cart(cart["id"])
            if "error" in cart_contents:
                print(f"❌ Failed to get cart: {cart_contents['error']}")
            else:
                if cart_contents.get("items"):
                    print(f"✅ Cart contains {len(cart_contents['items'])} items:")
                    for item in cart_contents["items"]:
                        print(f"   - {item['product_title']} ({item['variant_title']}) x{item['quantity']}")
                        print(f"     Price: {item['price']} {item['currency']}, Total: {item['line_total']}")
                    print(f"   Cart total: {cart_contents['total']} {cart_contents['currency']}")
                else:
                    print("✅ Cart is empty")
            
            print("\n" + "-" * 50)
            
            # Test 6: Checkout
            checkout = await client.test_start_checkout(cart["id"])
            if "error" in checkout:
                print(f"❌ Failed to start checkout: {checkout['error']}")
            else:
                print(f"✅ Checkout ready!")
                print(f"   Checkout URL: {checkout['checkout_url']}")
                print(f"   Total: {checkout['total_amount']} {checkout['currency']}")
            
            print("\n" + "-" * 50)
            
            # Test 7: Add shipping address
            if checkout and "checkout_id" in checkout:
                address = {
                    "first_name": "John",
                    "last_name": "Doe",
                    "address1": "123 Main St",
                    "city": "Anytown",
                    "state": "CA",
                    "zip": "12345",
                    "country": "US"
                }
                add_shipping_address_result = await client.test_add_shipping_address(checkout["checkout_id"], address)
                if "error" in add_shipping_address_result:
                    print(f"❌ Failed to add shipping address: {add_shipping_address_result['error']}")
                else:
                    print(f"✅ Shipping address added successfully")
            
            print("\n" + "-" * 50)
            
            # Test 8: Get shipping rates
            if checkout and "checkout_id" in checkout:
                shipping_rates = await client.test_get_shipping_rates(checkout["checkout_id"])
                if "error" in shipping_rates:
                    print(f"❌ Failed to get shipping rates: {shipping_rates['error']}")
                else:
                    print(f"✅ Available shipping rates:")
                    for rate in shipping_rates["rates"]:
                        print(f"   - {rate['name']} - {rate['price']} {rate['currency']}")
            
            print("\n" + "-" * 50)
            
            # Test 9: Select shipping rate
            if checkout and "checkout_id" in checkout and shipping_rates and "rates" in shipping_rates:
                selected_rate = shipping_rates["rates"][0]["handle"]
                select_shipping_rate_result = await client.test_select_shipping_rate(checkout["checkout_id"], selected_rate)
                if "error" in select_shipping_rate_result:
                    print(f"❌ Failed to select shipping rate: {select_shipping_rate_result['error']}")
                else:
                    print(f"✅ Shipping rate selected successfully")
            
            print("\n" + "-" * 50)
            
            # Test 10: Add payment
            if checkout and "checkout_id" in checkout:
                payment_info = {
                    "card_number": "4242424242424242",
                    "exp_month": 12,
                    "exp_year": 2024,
                    "cvc": "123"
                }
                add_payment_result = await client.test_add_payment(checkout["checkout_id"], payment_info)
                if "error" in add_payment_result:
                    print(f"❌ Failed to add payment: {add_payment_result['error']}")
                else:
                    print(f"✅ Payment added successfully")
            
            print("\n" + "-" * 50)
            
            # Test 11: Complete order
            if checkout and "checkout_id" in checkout:
                complete_order_result = await client.test_complete_order(checkout["checkout_id"])
                if "error" in complete_order_result:
                    print(f"❌ Failed to complete order: {complete_order_result['error']}")
                else:
                    print(f"✅ Order completed successfully!")
        
        print("\n🎉 All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
