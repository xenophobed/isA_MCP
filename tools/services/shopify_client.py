#!/usr/bin/env python
"""
Production Shopify Storefront API Client
专门用于真实Shopify API调用的生产级客户端
"""

import os
import json
import logging
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ShopifyClient:
    """Production Shopify Storefront API Client - 仅支持真实API"""
    
    def __init__(self):
        # 从环境变量加载配置
        self.store_domain = os.getenv('SHOPIFY_STORE_DOMAIN')
        self.storefront_token = os.getenv('SHOPIFY_STOREFRONT_ACCESS_TOKEN')
        self.admin_token = os.getenv('SHOPIFY_ADMIN_ACCESS_TOKEN')  # 可选
        self.api_version = os.getenv('SHOPIFY_API_VERSION', '2024-01')
        
        # 验证必需的配置
        if not self.store_domain:
            raise ValueError("SHOPIFY_STORE_DOMAIN environment variable is required")
        if not self.storefront_token:
            raise ValueError("SHOPIFY_STOREFRONT_ACCESS_TOKEN environment variable is required")
        
        # API URLs
        self.storefront_api_url = f"https://{self.store_domain}/api/{self.api_version}/graphql.json"
        self.admin_api_url = f"https://{self.store_domain}/admin/api/{self.api_version}"
        
        # Headers
        self.storefront_headers = {
            'Content-Type': 'application/json',
            'X-Shopify-Storefront-Access-Token': self.storefront_token,
            'Accept': 'application/json'
        }
        
        self.admin_headers = {
            'Content-Type': 'application/json',
            'X-Shopify-Access-Token': self.admin_token or '',
            'Accept': 'application/json'
        }
        
        # 购物车会话管理
        self.cart_id = None
        self.session_timeout = 3600  # 1小时
        self.cart_created_at = None
        
        # 缓存配置
        self.cache = {}
        self.cache_ttl = {
            'collections': 1800,  # 30分钟
            'products': 600,      # 10分钟
            'product_details': 300,  # 5分钟
        }
        
        logger.info(f"Shopify Client initialized for domain: {self.store_domain}")
    
    def _is_cache_valid(self, cache_key: str, cache_type: str) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self.cache:
            return False
        
        cached_item = self.cache[cache_key]
        ttl = self.cache_ttl.get(cache_type, 300)
        
        if datetime.now() - cached_item['timestamp'] > timedelta(seconds=ttl):
            del self.cache[cache_key]
            return False
        
        return True
    
    def _set_cache(self, cache_key: str, data: Any) -> None:
        """设置缓存"""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now()
        }
    
    def _get_cache(self, cache_key: str) -> Any:
        """获取缓存数据"""
        return self.cache[cache_key]['data']
    
    async def execute_graphql_query(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """执行GraphQL查询"""
        try:
            payload = {
                'query': query,
                'variables': variables or {}
            }
            
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.storefront_api_url,
                    headers=self.storefront_headers,
                    json=payload
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"GraphQL query failed: {response.status} {error_text}")
                        return {
                            "errors": [{
                                "message": f"API请求失败: {response.status}",
                                "extensions": {"code": response.status, "details": error_text}
                            }]
                        }
                    
                    result = await response.json()
                    
                    # 检查GraphQL错误
                    if 'errors' in result:
                        logger.error(f"GraphQL errors: {result['errors']}")
                    
                    return result
                    
        except asyncio.TimeoutError:
            logger.error("GraphQL query timeout")
            return {"errors": [{"message": "请求超时，请稍后重试"}]}
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error: {str(e)}")
            return {"errors": [{"message": f"网络请求错误: {str(e)}"}]}
        except Exception as e:
            logger.error(f"GraphQL query unexpected error: {str(e)}")
            return {"errors": [{"message": f"请求错误: {str(e)}"}]}
    
    async def execute_rest_api(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict:
        """执行REST API调用（Admin API）"""
        if not self.admin_token:
            return {"error": "Admin API token not configured"}
        
        try:
            url = f"{self.admin_api_url}/{endpoint.lstrip('/')}"
            
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                if method.upper() == "GET":
                    async with session.get(url, headers=self.admin_headers) as response:
                        return await response.json()
                elif method.upper() == "POST":
                    async with session.post(url, headers=self.admin_headers, json=data) as response:
                        return await response.json()
                elif method.upper() == "PUT":
                    async with session.put(url, headers=self.admin_headers, json=data) as response:
                        return await response.json()
                elif method.upper() == "DELETE":
                    async with session.delete(url, headers=self.admin_headers) as response:
                        return await response.json()
                else:
                    return {"error": f"Unsupported HTTP method: {method}"}
                        
        except Exception as e:
            logger.error(f"REST API error: {str(e)}")
            return {"error": str(e)}
    
    # === 商品分类管理 ===
    
    async def get_collections(self, first: int = 10, after: Optional[str] = None) -> Dict:
        """获取商品集合/分类"""
        cache_key = f"collections_{first}_{after}"
        
        if self._is_cache_valid(cache_key, 'collections'):
            logger.info("Returning cached collections")
            return self._get_cache(cache_key)
        
        query = """
        query GetCollections($first: Int!, $after: String) {
            collections(first: $first, after: $after) {
                pageInfo {
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                }
                edges {
                    cursor
                    node {
                        id
                        title
                        description
                        handle
                        updatedAt
                        image {
                            url
                            altText
                            width
                            height
                        }
                        products(first: 1) {
                            edges {
                                node {
                                    id
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        variables: Dict[str, Any] = {'first': first}
        if after:
            variables['after'] = after
            
        result = await self.execute_graphql_query(query, variables)
        
        if 'errors' not in result and 'data' in result:
            self._set_cache(cache_key, result)
        
        return result
    
    # === 商品搜索和获取 ===
    
    async def search_products(self, query: str, first: int = 10, after: Optional[str] = None, 
                            sort_key: str = "RELEVANCE", reverse: bool = False,
                            product_filters: Optional[List[Dict]] = None) -> Dict:
        """全局商品搜索"""
        cache_key = f"search_{query}_{first}_{after}_{sort_key}_{reverse}_{hash(str(product_filters))}"
        
        if self._is_cache_valid(cache_key, 'products'):
            return self._get_cache(cache_key)
        
        # 构建过滤器
        filters_str = ""
        if product_filters:
            filters_str = ", filters: $filters"
        
        search_query = f"""
        query SearchProducts($query: String!, $first: Int!, $after: String, $sortKey: ProductSortKeys!, $reverse: Boolean!{', $filters: [ProductFilter!]' if product_filters else ''}) {{
            products(first: $first, after: $after, query: $query, sortKey: $sortKey, reverse: $reverse{filters_str}) {{
                pageInfo {{
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                }}
                edges {{
                    cursor
                    node {{
                        id
                        title
                        description
                        handle
                        createdAt
                        updatedAt
                        availableForSale
                        totalInventory
                        vendor
                        productType
                        tags
                        priceRange {{
                            minVariantPrice {{
                                amount
                                currencyCode
                            }}
                            maxVariantPrice {{
                                amount
                                currencyCode
                            }}
                        }}
                        compareAtPriceRange {{
                            minVariantPrice {{
                                amount
                                currencyCode
                            }}
                            maxVariantPrice {{
                                amount
                                currencyCode
                            }}
                        }}
                        images(first: 3) {{
                            edges {{
                                node {{
                                    url
                                    altText
                                    width
                                    height
                                }}
                            }}
                        }}
                        variants(first: 5) {{
                            edges {{
                                node {{
                                    id
                                    title
                                    availableForSale
                                    quantityAvailable
                                    price {{
                                        amount
                                        currencyCode
                                    }}
                                    compareAtPrice {{
                                        amount
                                        currencyCode
                                    }}
                                }}
                            }}
                        }}
                    }}
                }}
            }}
        }}
        """
        
        variables = {
            'query': query,
            'first': first,
            'sortKey': sort_key,
            'reverse': reverse
        }
        
        if after:
            variables['after'] = after
        if product_filters:
            variables['filters'] = product_filters
        
        result = await self.execute_graphql_query(search_query, variables)
        
        if 'errors' not in result and 'data' in result:
            self._set_cache(cache_key, result)
        
        return result
    
    async def get_products_by_collection(self, collection_id: str, first: int = 10, 
                                       after: Optional[str] = None, sort_key: str = "COLLECTION_DEFAULT") -> Dict:
        """获取指定集合中的产品"""
        cache_key = f"collection_products_{collection_id}_{first}_{after}_{sort_key}"
        
        if self._is_cache_valid(cache_key, 'products'):
            return self._get_cache(cache_key)
        
        query = """
        query GetProductsByCollection($collectionId: ID!, $first: Int!, $after: String, $sortKey: ProductCollectionSortKeys!) {
            collection(id: $collectionId) {
                id
                title
                description
                handle
                image {
                    url
                    altText
                }
                products(first: $first, after: $after, sortKey: $sortKey) {
                    pageInfo {
                        hasNextPage
                        hasPreviousPage
                        startCursor
                        endCursor
                    }
                    edges {
                        cursor
                        node {
                            id
                            title
                            description
                            handle
                            availableForSale
                            totalInventory
                            vendor
                            productType
                            tags
                            priceRange {
                                minVariantPrice {
                                    amount
                                    currencyCode
                                }
                                maxVariantPrice {
                                    amount
                                    currencyCode
                                }
                            }
                            images(first: 2) {
                                edges {
                                    node {
                                        url
                                        altText
                                        width
                                        height
                                    }
                                }
                            }
                            variants(first: 3) {
                                edges {
                                    node {
                                        id
                                        title
                                        availableForSale
                                        quantityAvailable
                                        price {
                                            amount
                                            currencyCode
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        variables = {
            'collectionId': collection_id,
            'first': first,
            'sortKey': sort_key
        }
        
        if after:
            variables['after'] = after
        
        result = await self.execute_graphql_query(query, variables)
        
        if 'errors' not in result and 'data' in result:
            self._set_cache(cache_key, result)
        
        return result
    
    async def get_product_details(self, product_id: str) -> Dict:
        """获取商品详细信息"""
        cache_key = f"product_details_{product_id}"
        
        if self._is_cache_valid(cache_key, 'product_details'):
            return self._get_cache(cache_key)
        
        query = """
        query GetProductDetails($productId: ID!) {
            product(id: $productId) {
                id
                title
                description
                descriptionHtml
                handle
                availableForSale
                totalInventory
                vendor
                productType
                tags
                createdAt
                updatedAt
                onlineStoreUrl
                priceRange {
                    minVariantPrice {
                        amount
                        currencyCode
                    }
                    maxVariantPrice {
                        amount
                        currencyCode
                    }
                }
                compareAtPriceRange {
                    minVariantPrice {
                        amount
                        currencyCode
                    }
                    maxVariantPrice {
                        amount
                        currencyCode
                    }
                }
                images(first: 10) {
                    edges {
                        node {
                            url
                            altText
                            width
                            height
                        }
                    }
                }
                variants(first: 100) {
                    edges {
                        node {
                            id
                            title
                            availableForSale
                            quantityAvailable
                            price {
                                amount
                                currencyCode
                            }
                            compareAtPrice {
                                amount
                                currencyCode
                            }
                            selectedOptions {
                                name
                                value
                            }
                            image {
                                url
                                altText
                            }
                        }
                    }
                }
                options {
                    id
                    name
                    values
                }
                collections(first: 5) {
                    edges {
                        node {
                            id
                            title
                            handle
                        }
                    }
                }
            }
        }
        """
        
        variables = {'productId': product_id}
        result = await self.execute_graphql_query(query, variables)
        
        if 'errors' not in result and 'data' in result:
            self._set_cache(cache_key, result)
        
        return result
    
    # === 购物车管理 ===
    
    async def create_cart(self, lines: Optional[List[Dict]] = None, buyer_identity: Optional[Dict] = None) -> Dict:
        """创建购物车"""
        mutation = """
        mutation CreateCart($input: CartInput!) {
            cartCreate(input: $input) {
                cart {
                    id
                    checkoutUrl
                    createdAt
                    updatedAt
                    totalQuantity
                    lines(first: 50) {
                        edges {
                            node {
                                id
                                quantity
                                merchandise {
                                    ... on ProductVariant {
                                        id
                                        title
                                        product {
                                            id
                                            title
                                            handle
                                        }
                                        price {
                                            amount
                                            currencyCode
                                        }
                                        image {
                                            url
                                            altText
                                        }
                                    }
                                }
                                cost {
                                    totalAmount {
                                        amount
                                        currencyCode
                                    }
                                    subtotalAmount {
                                        amount
                                        currencyCode
                                    }
                                }
                            }
                        }
                    }
                    cost {
                        totalAmount {
                            amount
                            currencyCode
                        }
                        subtotalAmount {
                            amount
                            currencyCode
                        }
                        totalTaxAmount {
                            amount
                            currencyCode
                        }
                        totalDutyAmount {
                            amount
                            currencyCode
                        }
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        cart_input = {}
        if lines:
            cart_input['lines'] = lines
        if buyer_identity:
            cart_input['buyerIdentity'] = buyer_identity
        
        variables = {'input': cart_input}
        result = await self.execute_graphql_query(mutation, variables)
        
        # 保存购物车ID供后续使用
        if ('data' in result and 'cartCreate' in result['data'] and 
            result['data']['cartCreate']['cart']):
            self.cart_id = result['data']['cartCreate']['cart']['id']
            self.cart_created_at = datetime.now()
            logger.info(f"Cart created: {self.cart_id}")
        
        return result
    
    async def add_to_cart(self, variant_id: str, quantity: int = 1, attributes: Optional[List[Dict]] = None) -> Dict:
        """添加商品到购物车"""
        if not self.cart_id:
            await self.create_cart()
        
        # 检查购物车是否过期
        if (self.cart_created_at and 
            datetime.now() - self.cart_created_at > timedelta(seconds=self.session_timeout)):
            logger.info("Cart session expired, creating new cart")
            await self.create_cart()
        
        mutation = """
        mutation AddToCart($cartId: ID!, $lines: [CartLineInput!]!) {
            cartLinesAdd(cartId: $cartId, lines: $lines) {
                cart {
                    id
                    totalQuantity
                    lines(first: 50) {
                        edges {
                            node {
                                id
                                quantity
                                merchandise {
                                    ... on ProductVariant {
                                        id
                                        title
                                        product {
                                            id
                                            title
                                            handle
                                        }
                                        price {
                                            amount
                                            currencyCode
                                        }
                                        image {
                                            url
                                            altText
                                        }
                                    }
                                }
                                cost {
                                    totalAmount {
                                        amount
                                        currencyCode
                                    }
                                }
                                attributes {
                                    key
                                    value
                                }
                            }
                        }
                    }
                    cost {
                        totalAmount {
                            amount
                            currencyCode
                        }
                        subtotalAmount {
                            amount
                            currencyCode
                        }
                        totalTaxAmount {
                            amount
                            currencyCode
                        }
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        line_input = {
            'merchandiseId': variant_id,
            'quantity': quantity
        }
        
        if attributes:
            line_input['attributes'] = attributes
        
        variables = {
            'cartId': self.cart_id,
            'lines': [line_input]
        }
        
        return await self.execute_graphql_query(mutation, variables)
    
    async def get_cart(self) -> Dict:
        """获取购物车内容"""
        if not self.cart_id:
            return {"data": {"cart": None}}
        
        query = """
        query GetCart($cartId: ID!) {
            cart(id: $cartId) {
                id
                createdAt
                updatedAt
                checkoutUrl
                totalQuantity
                lines(first: 100) {
                    edges {
                        node {
                            id
                            quantity
                            merchandise {
                                ... on ProductVariant {
                                    id
                                    title
                                    availableForSale
                                    quantityAvailable
                                    product {
                                        id
                                        title
                                        handle
                                        productType
                                        vendor
                                    }
                                    price {
                                        amount
                                        currencyCode
                                    }
                                    compareAtPrice {
                                        amount
                                        currencyCode
                                    }
                                    image {
                                        url
                                        altText
                                        width
                                        height
                                    }
                                    selectedOptions {
                                        name
                                        value
                                    }
                                }
                            }
                            cost {
                                totalAmount {
                                    amount
                                    currencyCode
                                }
                                subtotalAmount {
                                    amount
                                    currencyCode
                                }
                            }
                            attributes {
                                key
                                value
                            }
                        }
                    }
                }
                cost {
                    totalAmount {
                        amount
                        currencyCode
                    }
                    subtotalAmount {
                        amount
                        currencyCode
                    }
                    totalTaxAmount {
                        amount
                        currencyCode
                    }
                    totalDutyAmount {
                        amount
                        currencyCode
                    }
                }
                buyerIdentity {
                    email
                    phone
                    countryCode
                }
            }
        }
        """
        
        variables = {'cartId': self.cart_id}
        return await self.execute_graphql_query(query, variables)
    
    async def update_cart_lines(self, line_updates: List[Dict]) -> Dict:
        """更新购物车商品"""
        if not self.cart_id:
            return {"errors": [{"message": "No active cart"}]}
        
        mutation = """
        mutation UpdateCartLines($cartId: ID!, $lines: [CartLineUpdateInput!]!) {
            cartLinesUpdate(cartId: $cartId, lines: $lines) {
                cart {
                    id
                    totalQuantity
                    lines(first: 100) {
                        edges {
                            node {
                                id
                                quantity
                                merchandise {
                                    ... on ProductVariant {
                                        id
                                        title
                                        product {
                                            title
                                        }
                                        price {
                                            amount
                                            currencyCode
                                        }
                                    }
                                }
                                cost {
                                    totalAmount {
                                        amount
                                        currencyCode
                                    }
                                }
                            }
                        }
                    }
                    cost {
                        totalAmount {
                            amount
                            currencyCode
                        }
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        variables = {
            'cartId': self.cart_id,
            'lines': line_updates
        }
        
        return await self.execute_graphql_query(mutation, variables)
    
    async def remove_from_cart(self, line_ids: List[str]) -> Dict:
        """从购物车移除商品"""
        if not self.cart_id:
            return {"errors": [{"message": "No active cart"}]}
        
        mutation = """
        mutation RemoveFromCart($cartId: ID!, $lineIds: [ID!]!) {
            cartLinesRemove(cartId: $cartId, lineIds: $lineIds) {
                cart {
                    id
                    totalQuantity
                    lines(first: 100) {
                        edges {
                            node {
                                id
                                quantity
                                merchandise {
                                    ... on ProductVariant {
                                        id
                                        title
                                        product {
                                            title
                                        }
                                    }
                                }
                            }
                        }
                    }
                    cost {
                        totalAmount {
                            amount
                            currencyCode
                        }
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        variables = {
            'cartId': self.cart_id,
            'lineIds': line_ids
        }
        
        return await self.execute_graphql_query(mutation, variables)
    
    # === 其他功能 ===
    
    async def get_product_recommendations(self, product_id: str, intent: str = "RELATED") -> Dict:
        """获取商品推荐"""
        query = """
        query GetProductRecommendations($productId: ID!, $intent: ProductRecommendationIntent!) {
            productRecommendations(productId: $productId, intent: $intent) {
                id
                title
                handle
                availableForSale
                priceRange {
                    minVariantPrice {
                        amount
                        currencyCode
                    }
                }
                images(first: 1) {
                    edges {
                        node {
                            url
                            altText
                        }
                    }
                }
                vendor
                productType
            }
        }
        """
        
        variables = {
            'productId': product_id,
            'intent': intent
        }
        
        return await self.execute_graphql_query(query, variables)
    
    async def get_shop_info(self) -> Dict:
        """获取店铺信息"""
        query = """
        query GetShopInfo {
            shop {
                id
                name
                description
                primaryDomain {
                    url
                    host
                }
                brand {
                    logo {
                        image {
                            url
                            altText
                        }
                    }
                    colors {
                        primary {
                            background
                            foreground
                        }
                        secondary {
                            background
                            foreground
                        }
                    }
                }
                paymentSettings {
                    acceptedCardBrands
                    countryCode
                    currencyCode
                }
            }
        }
        """
        
        return await self.execute_graphql_query(query)
    
    async def checkout(self) -> Dict:
        """获取结账URL"""
        if not self.cart_id:
            return {"error": "No active cart to checkout"}
        
        # 获取当前购物车信息
        cart_info = await self.get_cart()
        
        if ('data' in cart_info and cart_info['data']['cart'] and 
            cart_info['data']['cart']['checkoutUrl']):
            cart = cart_info['data']['cart']
            return {
                "success": True,
                "checkout_url": cart['checkoutUrl'],
                "cart_id": self.cart_id,
                "total_quantity": cart.get('totalQuantity', 0),
                "total_amount": cart['cost']['totalAmount']['amount'],
                "currency": cart['cost']['totalAmount']['currencyCode']
            }
        else:
            return {
                "success": False,
                "error": "Unable to generate checkout URL"
            }
    
    # === 缓存管理 ===
    
    def clear_cache(self) -> None:
        """清理缓存"""
        self.cache.clear()
        logger.info("Cache cleared")
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计"""
        return {
            "total_entries": len(self.cache),
            "cache_keys": list(self.cache.keys()),
            "cache_types": {
                cache_type: len([k for k in self.cache.keys() if cache_type in k])
                for cache_type in self.cache_ttl.keys()
            }
        }
    
    # === 会话管理 ===
    
    def reset_session(self) -> None:
        """重置会话状态"""
        self.cart_id = None
        self.cart_created_at = None
        logger.info("Session reset")
    
    def get_session_info(self) -> Dict:
        """获取会话信息"""
        return {
            "cart_id": self.cart_id,
            "cart_created_at": self.cart_created_at.isoformat() if self.cart_created_at else None,
            "session_active": self.cart_id is not None,
            "session_expired": (
                self.cart_created_at and 
                datetime.now() - self.cart_created_at > timedelta(seconds=self.session_timeout)
            ) if self.cart_created_at else False
        }