#!/usr/bin/env python3
"""
Test for Shopify tools - complete shopping workflow
Tests: search products -> view product -> add to cart -> checkout -> pay
"""
import json
import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

async def test_shopify_workflow():
    """Test the complete Shopify shopping workflow"""
    print("=== TESTING SHOPIFY SHOPPING WORKFLOW")
    print("=" * 50)
    
    try:
        # First test: Direct ShopifyClient test
        print("\n=== Test 1: Direct ShopifyClient test")
        from tools.services.shopify_service.shopify_client import ShopifyClient
        
        client = ShopifyClient()
        print(f"   ✓ ShopifyClient created: {type(client).__name__}")
        
        # Test search
        print("   Testing product search...")
        search_result = await client.search_products("", 3)  # Empty query returns all products
        print(f"   Search result keys: {list(search_result.keys()) if isinstance(search_result, dict) else 'Not a dict'}")
        
        if "data" in search_result and "products" in search_result["data"]:
            products = search_result["data"]["products"]["edges"]
            print(f"   ✓ Found {len(products)} products")
            
            # Get first product for testing
            if products:
                first_product = products[0]["node"]
                product_id = first_product["id"]
                print(f"   --> First product: {first_product.get('title', 'Unknown')} (ID: {product_id})")
                
                # Test product details
                print("   Testing product details...")
                details_result = await client.get_product_details(product_id)
                print(f"   Details result keys: {list(details_result.keys()) if isinstance(details_result, dict) else 'Not a dict'}")
                
                if "data" in details_result and "product" in details_result["data"]:
                    product = details_result["data"]["product"]
                    print(f"   ✓ Product details: {product.get('title', 'Unknown')}")
                    
                    # Get variant ID for cart test
                    if "variants" in product and "edges" in product["variants"] and product["variants"]["edges"]:
                        variant_id = product["variants"]["edges"][0]["node"]["id"]
                        print(f"   --> Variant ID: {variant_id}")
                        
                        # Test add to cart
                        print("   Testing add to cart...")
                        cart_result = await client.add_to_cart(variant_id, 1)
                        print(f"   Cart result keys: {list(cart_result.keys()) if isinstance(cart_result, dict) else 'Not a dict'}")
                        
                        if "data" in cart_result:
                            print(f"   ✓ Add to cart successful")
                            
                            # Test view cart
                            print("   Testing view cart...")
                            view_cart_result = await client.get_cart()
                            print(f"   View cart result keys: {list(view_cart_result.keys()) if isinstance(view_cart_result, dict) else 'Not a dict'}")
                        else:
                            print(f"   ✗ Add to cart failed")
                    else:
                        print(f"   ⚠ No variants found for product")
                else:
                    print(f"   ✗ Product details failed")
            else:
                print(f"   ⚠ No products found in search")
        else:
            print(f"   ✗ Search failed")
        
        print(f"\n=== Full search result:")
        print(f"   {search_result}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed with exception: {str(e)}")
        import traceback
        print(f"=== Full traceback:")
        print(traceback.format_exc())
        return False

async def test_shopify_tools_direct():
    """Test Shopify MCP tools directly"""
    print("\n=== TESTING SHOPIFY MCP TOOLS")
    print("=" * 50)
    
    try:
        # Import Shopify tools
        from tools.shopify_tools import register_realistic_shopify_tools
        
        # Mock security manager
        class MockSecurityManager:
            def security_check(self, func):
                return func
            def require_authorization(self, level):
                def decorator(func):
                    return func
                return decorator
        
        # Mock the security manager
        import tools.shopify_tools
        original_get_security_manager = tools.shopify_tools.get_security_manager
        tools.shopify_tools.get_security_manager = lambda: MockSecurityManager()
        
        # Create mock MCP and register tools
        class MockMCP:
            def __init__(self):
                self.tools = {}
            def tool(self):
                def decorator(func):
                    self.tools[func.__name__] = func
                    return func
                return decorator
        
        mock_mcp = MockMCP()
        register_realistic_shopify_tools(mock_mcp)
        tools.shopify_tools.get_security_manager = original_get_security_manager
        
        print(f"✓ Shopify tools registered: {list(mock_mcp.tools.keys())}")
        
        # Test workflow: search -> view -> add to cart -> checkout -> pay
        test_user_id = "test_user_123"
        
        # Step 1: Search products
        print(f"\n=== Step 1: Search products")
        search_tool = mock_mcp.tools.get('search_products')
        if search_tool:
            search_result_json = await search_tool(
                query="",  # Empty query returns all products
                limit=3,
                user_id=test_user_id
            )
            search_result = json.loads(search_result_json)
            print(f"   Search status: {search_result.get('status')}")
            
            if search_result.get('status') == 'success':
                products = search_result.get('data', {}).get('products', [])
                print(f"   ✓ Found {len(products)} products")
                
                if products:
                    # Step 2: Get product details
                    first_product = products[0]
                    product_id = first_product['id']
                    print(f"\n=== Step 2: Get product details for {first_product.get('title', 'Unknown')}")
                    
                    details_tool = mock_mcp.tools.get('get_product_details')
                    if details_tool:
                        details_result_json = await details_tool(product_id, test_user_id)
                        details_result = json.loads(details_result_json)
                        print(f"   Details status: {details_result.get('status')}")
                        
                        if details_result.get('status') == 'success':
                            product_details = details_result.get('data', {}).get('product', {})
                            variants = product_details.get('variants', [])
                            print(f"   ✓ Product details loaded, {len(variants)} variants")
                            
                            if variants:
                                # Step 3: Add to cart
                                variant_id = variants[0]['id']
                                print(f"\n=== Step 3: Add to cart (variant: {variant_id})")
                                
                                add_cart_tool = mock_mcp.tools.get('add_to_cart')
                                if add_cart_tool:
                                    cart_result_json = await add_cart_tool(variant_id, 1, test_user_id)
                                    cart_result = json.loads(cart_result_json)
                                    print(f"   Add to cart status: {cart_result.get('status')}")
                                    
                                    if cart_result.get('status') == 'success':
                                        cart_summary = cart_result.get('data', {}).get('cart_summary', {})
                                        print(f"   ✓ Added to cart: {cart_summary.get('total_items', 0)} items, ${cart_summary.get('total_amount', 0)}")
                                        
                                        # Step 4: View cart
                                        print(f"\n=== Step 4: View cart")
                                        view_cart_tool = mock_mcp.tools.get('view_cart')
                                        if view_cart_tool:
                                            view_result_json = await view_cart_tool(test_user_id)
                                            view_result = json.loads(view_result_json)
                                            print(f"   View cart status: {view_result.get('status')}")
                                            
                                            if view_result.get('status') == 'success':
                                                cart_data = view_result.get('data', {}).get('cart', {})
                                                cart_items = cart_data.get('items', [])
                                                print(f"   ✓ Cart contains {len(cart_items)} items")
                                                
                                                # Step 5: Start checkout
                                                print(f"\n=== Step 5: Start checkout")
                                                checkout_tool = mock_mcp.tools.get('start_checkout')
                                                if checkout_tool:
                                                    checkout_result_json = await checkout_tool(test_user_id)
                                                    checkout_result = json.loads(checkout_result_json)
                                                    print(f"   Checkout status: {checkout_result.get('status')}")
                                                    
                                                    if checkout_result.get('status') == 'success':
                                                        print(f"   ✓ Checkout started")
                                                        
                                                        # Step 6: Process payment (test)
                                                        print(f"\n=== Step 6: Process payment (test)")
                                                        payment_tool = mock_mcp.tools.get('process_payment')
                                                        if payment_tool:
                                                            payment_result_json = await payment_tool(
                                                                user_id=test_user_id,
                                                                card_number="4242424242424242",  # Test Visa
                                                                expiry_month="12",
                                                                expiry_year="25",
                                                                cvv="123",
                                                                billing_name="Test User"
                                                            )
                                                            payment_result = json.loads(payment_result_json)
                                                            print(f"   Payment status: {payment_result.get('status')}")
                                                            
                                                            if payment_result.get('status') == 'success':
                                                                payment_data = payment_result.get('data', {}).get('payment', {})
                                                                print(f"   ✓ Payment processed: {payment_data.get('payment_id', 'Unknown')}")
                                                                print(f"   --> Card type: {payment_data.get('card_type', 'Unknown')}")
                                                                print(f"   --> Amount: ${payment_data.get('amount', 0)} {payment_data.get('currency', 'USD')}")
                                                                
                                                                return True
                                                            else:
                                                                print(f"   ✗ Payment failed: {payment_result.get('data', {}).get('message', 'Unknown error')}")
        
        print(f"\n=== Workflow test completed")
        return False
        
    except Exception as e:
        print(f"\n✗ MCP tools test failed: {str(e)}")
        import traceback
        print(f"=== Full traceback:")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("=== Starting Shopify Tests...")
    
    # Test 1: Direct client test
    client_success = asyncio.run(test_shopify_workflow())
    
    # Test 2: MCP tools test
    tools_success = asyncio.run(test_shopify_tools_direct())
    
    print(f"\n=== TEST SUMMARY:")
    print(f"   Direct Client Test: {'✓ PASSED' if client_success else '✗ FAILED'}")
    print(f"   MCP Tools Test: {'✓ PASSED' if tools_success else '✗ FAILED'}")
    
    if client_success and tools_success:
        print("\n🎉 All tests completed successfully!")
    else:
        print("\n⚠ Some tests failed - check the logs above")