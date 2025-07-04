#!/usr/bin/env python
"""
Realistic Shopify Tools for Real Shopping Experience
实际的 Shopify 工具，支持真实购物体验
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from core.security import get_security_manager, SecurityLevel
from core.logging import get_logger
from core.database.supabase_client import get_supabase_client
from tools.services.shopify_service.shopify_client import ShopifyClient

logger = get_logger(__name__)

def register_shopify_tools(mcp):
    """注册实际的 Shopify 工具集"""
    
    security_manager = get_security_manager()
    
    try:
        shopify_client = ShopifyClient()
        logger.info("Shopify client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Shopify client: {e}")
        shopify_client = None
    
    # Supabase 客户端
    supabase = get_supabase_client()
    
    # ====== 产品搜索和浏览工具 ======
    
    @mcp.tool()
    @security_manager.security_check
    async def search_products(
        query: str = "", 
        category: str = "",
        price_min: float = 0,
        price_max: float = 0,
        sort_by: str = "relevance",
        limit: int = 5,
        user_id: str = "guest"
    ) -> str:
        """
        Search for products in Shopify store
        
        This tool searches through available products with filtering
        options for category, price range, and sorting preferences.
        
        Keywords: search, products, shopify, store, ecommerce, shop, buy
        Category: shopify
        
        Args:
            query: 搜索关键词
            category: 商品分类
            price_min: 最低价格
            price_max: 最高价格
            sort_by: 排序方式 (relevance, price_low, price_high, newest)
            limit: 返回结果数量
            user_id: 用户ID
        """
        if not shopify_client:
            return json.dumps({"status": "error", "message": "Shopping service unavailable"})
        
        try:
            # 构建搜索查询
            search_query = query
            if category:
                search_query += f" product_type:{category}"
            
            result = await shopify_client.search_products(search_query, limit)
            
            if "data" in result and "products" in result["data"]:
                products = []
                for edge in result["data"]["products"]["edges"]:
                    node = edge["node"]
                    
                    # 获取第一个图片和变体
                    image_url = ""
                    if "images" in node and "edges" in node["images"] and node["images"]["edges"]:
                        image_url = node["images"]["edges"][0]["node"]["url"]
                    
                    variant_info = {}
                    if "variants" in node and "edges" in node["variants"] and node["variants"]["edges"]:
                        variant = node["variants"]["edges"][0]["node"]
                        price = float(variant["price"]["amount"])
                        
                        # 价格过滤
                        if price_min > 0 and price < price_min:
                            continue
                        if price_max > 0 and price > price_max:
                            continue
                            
                        variant_info = {
                            "id": variant["id"],
                            "price": price,
                            "currency": variant["price"]["currencyCode"],
                            "available": variant["availableForSale"]
                        }
                    
                    if variant_info:  # 只添加有有效变体的产品
                        products.append({
                            "id": node["id"],
                            "title": node["title"],
                            "description": _truncate_text(node.get("description", ""), 200),
                            "handle": node["handle"],
                            "image_url": image_url,
                            "variant": variant_info,
                            "vendor": node.get("vendor", ""),
                            "available": node.get("availableForSale", False)
                        })
                
                return json.dumps({
                    "status": "success",
                    "data": {
                        "products": products,
                        "count": len(products),
                        "search_params": {
                            "query": query,
                            "category": category,
                            "price_range": f"${price_min}-${price_max}" if price_min or price_max else "Any"
                        }
                    }
                })
            else:
                return json.dumps({
                    "status": "success",
                    "data": {"products": [], "message": "No products found"}
                })
                
        except Exception as e:
            logger.error(f"Error searching products: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    @mcp.tool()
    @security_manager.security_check
    async def get_product_details(product_id: str, user_id: str = "guest") -> str:
        """
        Get detailed product information
        
        This tool retrieves comprehensive product details including
        images, variants, pricing, and availability information.
        
        Keywords: product, details, shopify, information, variants, price
        Category: shopify
        
        Args:
            product_id: 商品ID
            user_id: 用户ID
        """
        if not shopify_client:
            return json.dumps({"status": "error", "message": "Shopping service unavailable"})
        
        try:
            result = await shopify_client.get_product_details(product_id)
            
            if "data" in result and "product" in result["data"]:
                product = result["data"]["product"]
                
                # 处理图片
                images = []
                if "images" in product and "edges" in product["images"]:
                    for edge in product["images"]["edges"]:
                        images.append({
                            "url": edge["node"]["url"],
                            "alt": edge["node"].get("altText", "")
                        })
                
                # 处理变体
                variants = []
                if "variants" in product and "edges" in product["variants"]:
                    for edge in product["variants"]["edges"]:
                        variant = edge["node"]
                        variants.append({
                            "id": variant["id"],
                            "title": variant["title"],
                            "price": variant["price"]["amount"],
                            "currency": variant["price"]["currencyCode"],
                            "available": variant["availableForSale"],
                            "quantity_available": variant.get("quantityAvailable", 0),
                            "options": variant.get("selectedOptions", [])
                        })
                
                return json.dumps({
                    "status": "success",
                    "data": {
                        "product": {
                            "id": product["id"],
                            "title": product["title"],
                            "description": product.get("description", ""),
                            "vendor": product.get("vendor", ""),
                            "product_type": product.get("productType", ""),
                            "available": product["availableForSale"],
                            "images": images,
                            "variants": variants,
                            "price_range": {
                                "min": product["priceRange"]["minVariantPrice"]["amount"],
                                "max": product["priceRange"]["maxVariantPrice"]["amount"],
                                "currency": product["priceRange"]["minVariantPrice"]["currencyCode"]
                            }
                        }
                    }
                })
            else:
                return json.dumps({"status": "error", "message": "Product not found"})
                
        except Exception as e:
            logger.error(f"Error getting product details: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    # ====== 购物车管理工具 ======
    
    @mcp.tool()
    @security_manager.security_check
    async def add_to_cart(
        variant_id: str, 
        quantity: int = 1, 
        user_id: str = "guest"
    ) -> str:
        """
        Add product to shopping cart
        
        This tool adds selected product variants to the user's
        shopping cart with specified quantities.
        
        Keywords: cart, add, shopify, shopping, purchase, variant
        Category: shopify
        
        Args:
            variant_id: 商品变体ID
            quantity: 数量
            user_id: 用户ID
        """
        if not shopify_client:
            return json.dumps({"status": "error", "message": "Shopping service unavailable"})
        
        try:
            result = await shopify_client.add_to_cart(variant_id, quantity)
            
            if "data" in result and "cartLinesAdd" in result["data"]:
                cart_response = result["data"]["cartLinesAdd"]
                
                if cart_response.get("userErrors"):
                    return json.dumps({
                        "status": "error",
                        "message": "Failed to add item to cart",
                        "errors": cart_response["userErrors"]
                    })
                
                cart = cart_response["cart"]
                
                # 保存购物车到会话
                _save_cart_session(user_id, cart["id"], cart)
                
                return json.dumps({
                    "status": "success",
                    "data": {
                        "message": f"Added {quantity} item(s) to cart",
                        "cart_summary": {
                            "cart_id": cart["id"],
                            "total_items": cart.get("totalQuantity", 0),
                            "total_amount": cart["cost"]["totalAmount"]["amount"],
                            "currency": cart["cost"]["totalAmount"]["currencyCode"]
                        }
                    }
                })
            else:
                return json.dumps({"status": "error", "message": "Failed to add to cart"})
                
        except Exception as e:
            logger.error(f"Error adding to cart: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    @mcp.tool()
    @security_manager.security_check
    async def view_cart(user_id: str = "guest") -> str:
        """
        View shopping cart contents
        
        This tool displays all items currently in the user's
        shopping cart with quantities, prices, and totals.
        
        Keywords: cart, view, shopify, shopping, items, total
        Category: shopify
        
        Args:
            user_id: 用户ID
        """
        if not shopify_client:
            return json.dumps({"status": "error", "message": "Shopping service unavailable"})
        
        try:
            result = await shopify_client.get_cart()
            
            if "data" in result and result["data"].get("cart"):
                cart = result["data"]["cart"]
                
                # 处理购物车商品
                items = []
                if "lines" in cart and "edges" in cart["lines"]:
                    for edge in cart["lines"]["edges"]:
                        line = edge["node"]
                        merchandise = line["merchandise"]
                        
                        # Handle null image safely
                        image_url = ""
                        if merchandise.get("image") and isinstance(merchandise["image"], dict):
                            image_url = merchandise["image"].get("url", "")
                        
                        items.append({
                            "line_id": line["id"],
                            "quantity": line["quantity"],
                            "product": {
                                "title": merchandise["product"]["title"],
                                "variant_title": merchandise["title"],
                                "price": merchandise["price"]["amount"],
                                "currency": merchandise["price"]["currencyCode"],
                                "image_url": image_url
                            },
                            "line_total": line["cost"]["totalAmount"]["amount"]
                        })
                
                return json.dumps({
                    "status": "success",
                    "data": {
                        "cart": {
                            "cart_id": cart["id"],
                            "items": items,
                            "summary": {
                                "total_items": cart.get("totalQuantity", 0),
                                "subtotal": cart["cost"]["subtotalAmount"]["amount"],
                                "total": cart["cost"]["totalAmount"]["amount"],
                                "currency": cart["cost"]["totalAmount"]["currencyCode"]
                            }
                        }
                    }
                })
            else:
                return json.dumps({
                    "status": "success",
                    "data": {
                        "cart": {"items": [], "summary": {"total_items": 0}},
                        "message": "Cart is empty"
                    }
                })
                
        except Exception as e:
            logger.error(f"Error viewing cart: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    # ====== 用户信息管理工具 ======
    
    @mcp.tool()
    @security_manager.security_check
    async def get_user_info(user_id: str, info_type: str = "all") -> str:
        """
        Get user information (address, payment methods, etc.)
        
        This tool retrieves stored user information including
        shipping addresses, payment methods, and preferences.
        
        Keywords: user, info, profile, address, payment, preferences
        Category: shopify
        
        Args:
            user_id: 用户ID
            info_type: 信息类型 (all, shipping, payment, preferences)
        """
        try:
            # 查询用户信息，用 auth0_id 或 email 作为查找条件
            result = supabase.client.table('users').select('*').or_(f'auth0_id.eq.{user_id},email.eq.{user_id}').execute()
            
            if result.data:
                user = result.data[0]
                
                user_data = {
                    "user_id": user.get('id'),
                    "auth0_id": user.get('auth0_id'),
                    "email": user.get('email'),
                    "name": user.get('name'),
                    "phone": user.get('phone'),
                    "shipping_addresses": user.get('shipping_addresses', []),
                    "payment_methods": user.get('payment_methods', []),
                    "preferences": user.get('preferences', {}),
                    "credits_remaining": user.get('credits_remaining'),
                    "subscription_status": user.get('subscription_status')
                }
                
                if info_type != "all":
                    if info_type == "shipping":
                        user_data = {"shipping_addresses": user_data["shipping_addresses"]}
                    elif info_type == "payment":
                        user_data = {"payment_methods": user_data["payment_methods"]}
                    elif info_type == "preferences":
                        user_data = {"preferences": user_data["preferences"]}
                
                return json.dumps({
                    "status": "success",
                    "data": {"user_info": user_data}
                })
            else:
                return json.dumps({
                    "status": "success",
                    "data": {"user_info": None, "message": "User not found - first time customer"}
                })
                
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    @mcp.tool()
    @security_manager.security_check
    async def save_shipping_address(
        user_id: str,
        name: str,
        address_line1: str,
        address_line2: str = "",
        city: str = "",
        state: str = "",
        postal_code: str = "",
        country: str = "US",
        phone: str = "",
        is_default: bool = False
    ) -> str:
        """
        Save user shipping address
        
        This tool stores shipping address information for users
        to enable faster checkout and delivery options.
        
        Keywords: shipping, address, save, delivery, checkout, user
        Category: shopify
        
        Args:
            user_id: 用户ID
            name: 收件人姓名
            address_line1: 地址第一行
            address_line2: 地址第二行
            city: 城市
            state: 州/省
            postal_code: 邮政编码
            country: 国家
            phone: 电话
            is_default: 是否为默认地址
        """
        try:
            # 查询用户信息，用 auth0_id 或 email 作为查找条件
            result = supabase.client.table('users').select('*').or_(f'auth0_id.eq.{user_id},email.eq.{user_id}').execute()
            
            if result.data:
                user = result.data[0]
                addresses = user.get('shipping_addresses', [])
                
                # 新地址
                new_address = {
                    "id": f"addr_{len(addresses) + 1}",
                    "name": name,
                    "address_line1": address_line1,
                    "address_line2": address_line2,
                    "city": city,
                    "state": state,
                    "postal_code": postal_code,
                    "country": country,
                    "phone": phone,
                    "is_default": is_default,
                    "created_at": datetime.now().isoformat()
                }
                
                # 如果设为默认，清除其他默认标记
                if is_default:
                    for addr in addresses:
                        addr["is_default"] = False
                
                addresses.append(new_address)
                
                # 更新用户地址
                supabase.client.table('users').update({
                    'shipping_addresses': addresses,
                    'updated_at': datetime.now().isoformat()
                }).eq('id', user['id']).execute()
            else:
                # 用户不存在，创建新用户（这种情况比较少见）
                return json.dumps({
                    "status": "error", 
                    "message": "User not found. Please register first."
                })
            
            return json.dumps({
                "status": "success",
                "data": {
                    "message": "Shipping address saved successfully",
                    "address": new_address
                }
            })
            
        except Exception as e:
            logger.error(f"Error saving shipping address: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    # ====== 结账工具 ======
    
    @mcp.tool()
    @security_manager.security_check
    async def start_checkout(user_id: str = "guest") -> str:
        """
        Start checkout process
        
        This tool initiates the checkout flow for items in the
        shopping cart, preparing for payment and delivery.
        
        Keywords: checkout, payment, order, process, cart, purchase
        Category: shopify
        
        Args:
            user_id: 用户ID
        """
        if not shopify_client:
            return json.dumps({"status": "error", "message": "Shopping service unavailable"})
        
        try:
            # 获取购物车
            cart_result = await shopify_client.get_cart()
            
            if not (cart_result.get("data") and cart_result["data"].get("cart")):
                return json.dumps({
                    "status": "error",
                    "message": "No items in cart to checkout"
                })
            
            cart = cart_result["data"]["cart"]
            
            # 获取用户信息
            user_info_result = await get_user_info(user_id)
            user_info_data = json.loads(user_info_result)
            
            checkout_data = {
                "cart_id": cart["id"],
                "cart_summary": {
                    "total_items": cart.get("totalQuantity", 0),
                    "total_amount": cart["cost"]["totalAmount"]["amount"],
                    "currency": cart["cost"]["totalAmount"]["currencyCode"]
                },
                "user_info": user_info_data.get("data", {}).get("user_info"),
                "checkout_url": cart.get("checkoutUrl", ""),
                "requires_shipping": True,
                "requires_payment": True
            }
            
            # 如果是已知用户且有地址信息，可以预填充
            if checkout_data["user_info"] and checkout_data["user_info"]["shipping_addresses"]:
                default_address = None
                for addr in checkout_data["user_info"]["shipping_addresses"]:
                    if addr.get("is_default"):
                        default_address = addr
                        break
                if default_address:
                    checkout_data["suggested_shipping"] = default_address
            
            return json.dumps({
                "status": "success",
                "data": checkout_data
            })
            
        except Exception as e:
            logger.error(f"Error starting checkout: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    @mcp.tool()
    @security_manager.security_check
    async def process_payment(
        user_id: str,
        payment_method_id: str = "",
        card_number: str = "",
        expiry_month: str = "",
        expiry_year: str = "",
        cvv: str = "",
        billing_name: str = "",
        save_payment_method: bool = False
    ) -> str:
        """
        Process payment (test environment)
        
        This tool handles payment processing for checkout,
        supporting various payment methods and test card numbers.
        
        Keywords: payment, process, card, checkout, order, billing
        Category: shopify
        
        Args:
            user_id: 用户ID
            payment_method_id: 已保存的支付方式ID
            card_number: 卡号（测试环境可用测试卡号）
            expiry_month: 过期月份
            expiry_year: 过期年份
            cvv: 安全码
            billing_name: 账单姓名
            save_payment_method: 是否保存支付方式
        """
        try:
            # 获取购物车总额
            cart_result = await shopify_client.get_cart()
            if not (cart_result.get("data") and cart_result["data"].get("cart")):
                return json.dumps({
                    "status": "error",
                    "message": "No cart found"
                })
            
            cart = cart_result["data"]["cart"]
            amount = cart["cost"]["totalAmount"]["amount"]
            currency = cart["cost"]["totalAmount"]["currencyCode"]
            
            # 如果使用已保存的支付方式
            if payment_method_id:
                # 从数据库获取支付方式（实际中应该是tokenized的）
                try:
                    result = supabase.client.table('users').select('payment_methods').or_(f'auth0_id.eq.{user_id},email.eq.{user_id}').execute()
                    if result.data:
                        payment_methods = result.data[0].get('payment_methods', [])
                        payment_method = next((pm for pm in payment_methods if pm["id"] == payment_method_id), None)
                        if payment_method:
                            card_number = payment_method["masked_number"]
                except Exception as e:
                    logger.error(f"Error getting payment method: {e}")
            
            # 验证测试卡号
            test_cards = {
                "4242424242424242": "visa",
                "5555555555554444": "mastercard",
                "378282246310005": "amex"
            }
            
            card_type = test_cards.get(card_number, "unknown")
            
            if card_number not in test_cards:
                return json.dumps({
                    "status": "error",
                    "message": "Invalid card number. Use test card numbers: 4242424242424242 (Visa), 5555555555554444 (Mastercard)"
                })
            
            # 模拟支付处理
            payment_result = {
                "payment_id": f"pay_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "status": "succeeded",
                "amount": amount,
                "currency": currency,
                "card_type": card_type,
                "last4": card_number[-4:],
                "processed_at": datetime.now().isoformat()
            }
            
            # 保存支付方式（如果用户选择）
            if save_payment_method and not payment_method_id:
                await _save_payment_method(user_id, card_number, expiry_month, expiry_year, billing_name, card_type)
            
            return json.dumps({
                "status": "success",
                "data": {
                    "payment": payment_result,
                    "message": "Payment processed successfully",
                    "next_step": "order_confirmation"
                }
            })
            
        except Exception as e:
            logger.error(f"Error processing payment: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    # ====== 辅助函数 ======
    
    def _save_cart_session(user_id: str, cart_id: str, cart_data: dict):
        """保存购物车会话"""
        try:
            session_id = f"sess_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            expires_at = datetime.now().replace(hour=23, minute=59, second=59).isoformat()
            
            # 先检查是否存在该用户的会话，如果存在则更新，否则插入
            supabase.client.table('user_sessions').upsert({
                'session_id': session_id,
                'user_id': user_id,
                'cart_data': cart_data,
                'created_at': datetime.now().isoformat(),
                'expires_at': expires_at
            }).execute()
        except Exception as e:
            logger.error(f"Error saving cart session: {e}")
    
    async def _save_payment_method(user_id: str, card_number: str, expiry_month: str, expiry_year: str, billing_name: str, card_type: str):
        """保存支付方式（实际中应该tokenize）"""
        try:
            # 查询用户信息，用 auth0_id 或 email 作为查找条件
            result = supabase.client.table('users').select('*').or_(f'auth0_id.eq.{user_id},email.eq.{user_id}').execute()
            
            if result.data:
                user = result.data[0]
                payment_methods = user.get('payment_methods', [])
                
                new_payment_method = {
                    "id": f"pm_{len(payment_methods) + 1}",
                    "card_type": card_type,
                    "masked_number": f"****-****-****-{card_number[-4:]}",
                    "expiry": f"{expiry_month}/{expiry_year}",
                    "billing_name": billing_name,
                    "created_at": datetime.now().isoformat()
                }
                
                payment_methods.append(new_payment_method)
                
                # 更新用户支付方式
                supabase.client.table('users').update({
                    'payment_methods': payment_methods,
                    'updated_at': datetime.now().isoformat()
                }).eq('id', user['id']).execute()
            else:
                logger.warning(f"User {user_id} not found when saving payment method")
        except Exception as e:
            logger.error(f"Error saving payment method: {e}")
    
    def _truncate_text(text: str, max_length: int) -> str:
        """截断文本"""
        if len(text) <= max_length:
            return text
        return text[:max_length].rsplit(' ', 1)[0] + "..."

    logger.info("Realistic Shopify tools registered successfully")