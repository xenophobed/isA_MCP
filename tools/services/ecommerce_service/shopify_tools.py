#!/usr/bin/env python3
"""
Realistic Shopify Tools for Real Shopping Experience
Shopify ecommerce tools based on BaseTool for real shopping functionality
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP
from tools.base_tool import BaseTool
from core.security import get_security_manager, SecurityLevel
from core.logging import get_logger
from core.database.supabase_client import get_supabase_client
from tools.services.ecommerce_service.shopify_client import ShopifyClient

logger = get_logger(__name__)

class ShopifyToolsManager(BaseTool):
    """Shopify ecommerce tools manager for real shopping functionality"""
    
    def __init__(self):
        super().__init__()
        self.supabase = get_supabase_client()
        
        try:
            self.shopify_client = ShopifyClient()
            logger.info("Shopify client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Shopify client: {e}")
            self.shopify_client = None

    async def search_products(
        self,
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
        
        Args:
            query: Search keywords
            category: Product category
            price_min: Minimum price
            price_max: Maximum price
            sort_by: Sort method (relevance, price_low, price_high, newest)
            limit: Number of results to return
            user_id: User ID
        """
        if not self.shopify_client:
            return self.create_response(
                "error", 
                "search_products", 
                {}, 
                "Shopping service unavailable"
            )
        
        try:
            # Build search query
            search_query = query
            if category:
                search_query += f" product_type:{category}"
            
            result = await self.shopify_client.search_products(search_query, limit)
            
            if "data" in result and "products" in result["data"]:
                products = []
                for edge in result["data"]["products"]["edges"]:
                    node = edge["node"]
                    
                    # Get first image and variant
                    image_url = ""
                    if "images" in node and "edges" in node["images"] and node["images"]["edges"]:
                        image_url = node["images"]["edges"][0]["node"]["url"]
                    
                    variant_info = {}
                    if "variants" in node and "edges" in node["variants"] and node["variants"]["edges"]:
                        variant = node["variants"]["edges"][0]["node"]
                        price = float(variant["price"]["amount"])
                        
                        # Price filtering
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
                    
                    if variant_info:  # Only add products with valid variants
                        products.append({
                            "id": node["id"],
                            "title": node["title"],
                            "description": self._truncate_text(node.get("description", ""), 200),
                            "handle": node["handle"],
                            "image_url": image_url,
                            "variant": variant_info,
                            "vendor": node.get("vendor", ""),
                            "available": node.get("availableForSale", False)
                        })
                
                return self.create_response(
                    "success",
                    "search_products",
                    {
                        "products": products,
                        "count": len(products),
                        "search_params": {
                            "query": query,
                            "category": category,
                            "price_range": f"${price_min}-${price_max}" if price_min or price_max else "Any"
                        }
                    }
                )
            else:
                return self.create_response(
                    "success",
                    "search_products",
                    {"products": [], "message": "No products found"}
                )
                
        except Exception as e:
            logger.error(f"Error searching products: {e}")
            return self.create_response("error", "search_products", {}, str(e))

    async def get_product_details(self, product_id: str, user_id: str = "guest") -> str:
        """
        Get detailed product information
        
        Args:
            product_id: Product ID
            user_id: User ID
        """
        if not self.shopify_client:
            return self.create_response(
                "error", 
                "get_product_details", 
                {}, 
                "Shopping service unavailable"
            )
        
        try:
            result = await self.shopify_client.get_product_details(product_id)
            
            if "data" in result and "product" in result["data"]:
                product = result["data"]["product"]
                
                # Process images
                images = []
                if "images" in product and "edges" in product["images"]:
                    for edge in product["images"]["edges"]:
                        images.append({
                            "url": edge["node"]["url"],
                            "alt": edge["node"].get("altText", "")
                        })
                
                # Process variants
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
                
                return self.create_response(
                    "success",
                    "get_product_details",
                    {
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
                )
            else:
                return self.create_response("error", "get_product_details", {}, "Product not found")
                
        except Exception as e:
            logger.error(f"Error getting product details: {e}")
            return self.create_response("error", "get_product_details", {}, str(e))

    async def add_to_cart(
        self,
        variant_id: str, 
        quantity: int = 1, 
        user_id: str = "guest"
    ) -> str:
        """
        Add product to shopping cart
        
        Args:
            variant_id: Product variant ID
            quantity: Quantity
            user_id: User ID
        """
        if not self.shopify_client:
            return self.create_response(
                "error", 
                "add_to_cart", 
                {}, 
                "Shopping service unavailable"
            )
        
        try:
            result = await self.shopify_client.add_to_cart(variant_id, quantity)
            
            if "data" in result and "cartLinesAdd" in result["data"]:
                cart_response = result["data"]["cartLinesAdd"]
                
                if cart_response.get("userErrors"):
                    return self.create_response(
                        "error",
                        "add_to_cart",
                        {"errors": cart_response["userErrors"]},
                        "Failed to add item to cart"
                    )
                
                cart = cart_response["cart"]
                
                # Save cart session
                self._save_cart_session(user_id, cart["id"], cart)
                
                return self.create_response(
                    "success",
                    "add_to_cart",
                    {
                        "message": f"Added {quantity} item(s) to cart",
                        "cart_summary": {
                            "cart_id": cart["id"],
                            "total_items": cart.get("totalQuantity", 0),
                            "total_amount": cart["cost"]["totalAmount"]["amount"],
                            "currency": cart["cost"]["totalAmount"]["currencyCode"]
                        }
                    }
                )
            else:
                return self.create_response("error", "add_to_cart", {}, "Failed to add to cart")
                
        except Exception as e:
            logger.error(f"Error adding to cart: {e}")
            return self.create_response("error", "add_to_cart", {}, str(e))

    async def view_cart(self, user_id: str = "guest") -> str:
        """
        View shopping cart contents
        
        Args:
            user_id: User ID
        """
        if not self.shopify_client:
            return self.create_response(
                "error", 
                "view_cart", 
                {}, 
                "Shopping service unavailable"
            )
        
        try:
            result = await self.shopify_client.get_cart()
            
            if "data" in result and result["data"].get("cart"):
                cart = result["data"]["cart"]
                
                # Process cart items
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
                
                return self.create_response(
                    "success",
                    "view_cart",
                    {
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
                )
            else:
                return self.create_response(
                    "success",
                    "view_cart",
                    {
                        "cart": {"items": [], "summary": {"total_items": 0}},
                        "message": "Cart is empty"
                    }
                )
                
        except Exception as e:
            logger.error(f"Error viewing cart: {e}")
            return self.create_response("error", "view_cart", {}, str(e))

    def _save_cart_session(self, user_id: str, cart_id: str, cart_data: dict):
        """Save cart session"""
        try:
            session_id = f"sess_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            expires_at = datetime.now().replace(hour=23, minute=59, second=59).isoformat()
            
            # Check if user session exists, update if exists, otherwise insert
            self.supabase.client.table('user_sessions').upsert({
                'session_id': session_id,
                'user_id': user_id,
                'cart_data': cart_data,
                'created_at': datetime.now().isoformat(),
                'expires_at': expires_at
            }).execute()
        except Exception as e:
            logger.error(f"Error saving cart session: {e}")
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text"""
        if len(text) <= max_length:
            return text
        return text[:max_length].rsplit(' ', 1)[0] + "..."

def register_shopify_tools(mcp: FastMCP):
    """Register Shopify ecommerce tools"""
    shopify_manager = ShopifyToolsManager()
    
    @mcp.tool()
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
            query: Search keywords
            category: Product category
            price_min: Minimum price
            price_max: Maximum price
            sort_by: Sort method (relevance, price_low, price_high, newest)
            limit: Number of results to return
            user_id: User ID
        """
        return await shopify_manager.search_products(
            query, category, price_min, price_max, sort_by, limit, user_id
        )
    
    @mcp.tool()
    async def get_product_details(product_id: str, user_id: str = "guest") -> str:
        """
        Get detailed product information
        
        This tool retrieves comprehensive product details including
        images, variants, pricing, and availability information.
        
        Keywords: product, details, shopify, information, variants, price
        Category: shopify
        
        Args:
            product_id: Product ID
            user_id: User ID
        """
        return await shopify_manager.get_product_details(product_id, user_id)
    
    @mcp.tool()
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
            variant_id: Product variant ID
            quantity: Quantity
            user_id: User ID
        """
        return await shopify_manager.add_to_cart(variant_id, quantity, user_id)
    
    @mcp.tool()
    async def view_cart(user_id: str = "guest") -> str:
        """
        View shopping cart contents
        
        This tool displays all items currently in the user's
        shopping cart with quantities, prices, and totals.
        
        Keywords: cart, view, shopify, shopping, items, total
        Category: shopify
        
        Args:
            user_id: User ID
        """
        return await shopify_manager.view_cart(user_id)
    
    print("🛒 Shopify ecommerce tools registered successfully")