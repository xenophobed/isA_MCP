#!/usr/bin/env python
"""
Enhanced Shopify Storefront API客户端
提供与Shopify商店交互的完整API封装，支持真实API和模拟数据
"""

import os
import json
import logging
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class EnhancedShopifyClient:
    """Enhanced Shopify Storefront API客户端，支持真实API和智能缓存"""
    
    def __init__(self, use_real_api: bool = None):
        # 从环境变量加载配置
        self.store_domain = os.getenv('SHOPIFY_STORE_DOMAIN', 'example.myshopify.com')
        self.storefront_token = os.getenv('SHOPIFY_STOREFRONT_ACCESS_TOKEN')
        self.admin_token = os.getenv('SHOPIFY_ADMIN_ACCESS_TOKEN')
        self.api_version = os.getenv('SHOPIFY_API_VERSION', '2024-01')
        
        # API URLs
        self.storefront_api_url = f"https://{self.store_domain}/api/{self.api_version}/graphql.json"
        self.admin_api_url = f"https://{self.store_domain}/admin/api/{self.api_version}"
        
        # Headers
        self.storefront_headers = {
            'Content-Type': 'application/json',
            'X-Shopify-Storefront-Access-Token': self.storefront_token or 'dummy_token'
        }
        
        self.admin_headers = {
            'Content-Type': 'application/json',
            'X-Shopify-Access-Token': self.admin_token or 'dummy_token'
        }
        
        # 决定是否使用真实API
        if use_real_api is None:
            # 自动检测：如果有token且domain不是example，使用真实API
            self.use_real_api = (
                self.storefront_token and 
                self.storefront_token != 'dummy_token' and 
                'example' not in self.store_domain
            )
        else:
            self.use_real_api = use_real_api
        
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
        
        logger.info(f"Enhanced Shopify Client initialized - Real API: {self.use_real_api}")
    
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
        if not self.use_real_api:
            logger.info("Using mock data for GraphQL query")
            return self._get_mock_data(query, variables)
        
        try:
            payload = {
                'query': query,
                'variables': variables or {}
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.storefront_api_url,
                    headers=self.storefront_headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"GraphQL query failed: {response.status} {error_text}")
                        return {"errors": [{"message": f"API请求失败: {response.status}"}]}
                    
                    result = await response.json()
                    return result
                    
        except asyncio.TimeoutError:
            logger.error("GraphQL query timeout")
            return {"errors": [{"message": "请求超时"}]}
        except Exception as e:
            logger.error(f"GraphQL query error: {str(e)}")
            return {"errors": [{"message": f"请求错误: {str(e)}"}]}
    
    async def execute_rest_api(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict:
        """执行REST API调用（Admin API）"""
        if not self.use_real_api:
            logger.info("Using mock data for REST API")
            return {"mock": True, "endpoint": endpoint}
        
        try:
            url = f"{self.admin_api_url}/{endpoint}"
            
            async with aiohttp.ClientSession() as session:
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
                        
        except Exception as e:
            logger.error(f"REST API error: {str(e)}")
            return {"error": str(e)}
    
    # 原有的模拟数据方法保持不变
    def _get_mock_data(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """根据查询类型返回模拟数据"""
        if "GetCollections" in query or "collections" in query.lower():
            return self._mock_collections_data()
        elif "GetProductsByCollection" in query or "collection" in query.lower():
            return self._mock_products_by_collection_data(variables.get('collectionId') if variables else None)
        elif "GetProductDetails" in query or "product" in query.lower():
            return self._mock_product_details_data(variables.get('productId') if variables else None)
        elif "cartCreate" in query:
            return self._mock_cart_create_data()
        elif "cartLinesAdd" in query:
            return self._mock_cart_add_data(variables)
        elif "cart" in query.lower():
            return self._mock_cart_get_data()
        elif "search" in query.lower():
            return self._mock_search_results(variables.get('query') if variables else "")
        else:
            return {"data": {}}
    
    def _mock_collections_data(self) -> Dict:
        """模拟集合数据 - 扩展版"""
        return {
            "data": {
                "collections": {
                    "edges": [
                        {
                            "node": {
                                "id": "gid://shopify/Collection/111",
                                "title": "夏季系列",
                                "description": "2024夏季最新系列产品，清爽舒适",
                                "handle": "summer-collection",
                                "image": {"url": "https://example.com/images/summer.jpg", "altText": "夏季系列图片"},
                                "productsCount": 15
                            }
                        },
                        {
                            "node": {
                                "id": "gid://shopify/Collection/222",
                                "title": "商务装",
                                "description": "专业商务正装系列",
                                "handle": "business-collection",
                                "image": {"url": "https://example.com/images/business.jpg", "altText": "商务装系列图片"},
                                "productsCount": 12
                            }
                        },
                        {
                            "node": {
                                "id": "gid://shopify/Collection/333",
                                "title": "约会装",
                                "description": "浪漫约会服装系列",
                                "handle": "date-collection",
                                "image": {"url": "https://example.com/images/date.jpg", "altText": "约会装系列图片"},
                                "productsCount": 18
                            }
                        },
                        {
                            "node": {
                                "id": "gid://shopify/Collection/444",
                                "title": "运动休闲",
                                "description": "舒适运动休闲装",
                                "handle": "casual-collection",
                                "image": {"url": "https://example.com/images/casual.jpg", "altText": "运动休闲系列图片"},
                                "productsCount": 20
                            }
                        }
                    ]
                }
            }
        }
    
    def _mock_products_by_collection_data(self, collection_id: str) -> Dict:
        """模拟集合中的产品数据 - 扩展版"""
        products_by_collection = {
            "gid://shopify/Collection/111": {  # 夏季系列
                "title": "夏季系列",
                "products": [
                    {
                        "id": "gid://shopify/Product/1001",
                        "title": "亚麻短袖衬衫",
                        "description": "透气舒适的纯亚麻衬衫，适合夏季穿着",
                        "handle": "linen-shirt",
                        "priceRange": {"minVariantPrice": {"amount": "299.00", "currencyCode": "CNY"}},
                    "images": {
                        "edges": [
                            {"node": {"url": "https://example.com/images/linen-shirt-1.jpg", "altText": "亚麻衬衫正面"}},
                            {"node": {"url": "https://example.com/images/linen-shirt-2.jpg", "altText": "亚麻衬衫背面"}}
                        ]
                    },
                    "variants": {
                        "edges": [
                            {
                                "node": {
                                    "id": "gid://shopify/ProductVariant/10001",
                                    "title": "S / 白色",
                                    "price": {"amount": "299.00", "currencyCode": "CNY"},
                                    "availableForSale": True
                                }
                            },
                            {
                                "node": {
                                    "id": "gid://shopify/ProductVariant/10002",
                                    "title": "M / 白色",
                                    "price": {"amount": "299.00", "currencyCode": "CNY"},
                                    "availableForSale": True
                                }
                            },
                            {
                                "node": {
                                    "id": "gid://shopify/ProductVariant/10003",
                                    "title": "L / 蓝色",
                                    "price": {"amount": "299.00", "currencyCode": "CNY"},
                                    "availableForSale": True
                                }
                            }
                        ]
                    },
                    "tags": ["夏季", "透气", "舒适", "商务休闲"],
                    "vendor": "优质服装品牌",
                    "productType": "衬衫"
                }
            }
        }
    
    def _mock_cart_create_data(self) -> Dict:
        """模拟创建购物车数据"""
        self.cart_id = f"gid://shopify/Cart/cart_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.cart_created_at = datetime.now()
        return {
            "data": {
                "cartCreate": {
                    "cart": {
                        "id": self.cart_id,
                        "checkoutUrl": f"https://{self.store_domain}/cart/{self.cart_id.split('/')[-1]}",
                        "createdAt": self.cart_created_at.isoformat(),
                        "updatedAt": self.cart_created_at.isoformat(),
                        "lines": {"edges": []},
                        "estimatedCost": {
                            "totalAmount": {"amount": "0.00", "currencyCode": "CNY"}
                        }
                    },
                    "userErrors": []
                }
            }
        }
    
    def _mock_cart_add_data(self, variables: Dict) -> Dict:
        """模拟添加商品到购物车数据"""
        if not self.cart_id:
            self._mock_cart_create_data()
            
        lines = variables.get('lines', [{}])
        variant_id = lines[0].get('merchandiseId', '') if lines else ''
        quantity = lines[0].get('quantity', 1) if lines else 1
        
        return {
            "data": {
                "cartLinesAdd": {
                    "cart": {
                        "id": self.cart_id,
                        "lines": {
                            "edges": [
                                {
                                    "node": {
                                        "id": f"gid://shopify/CartLine/{datetime.now().timestamp()}",
                                        "quantity": quantity,
                                        "merchandise": {
                                            "id": variant_id,
                                            "title": "S / 白色",
                                            "product": {"title": "亚麻短袖衬衫"},
                                            "price": {"amount": "299.00", "currencyCode": "CNY"}
                                        },
                                        "cost": {
                                            "totalAmount": {
                                                "amount": str(float(299.00) * quantity),
                                                "currencyCode": "CNY"
                                            }
                                        }
                                    }
                                }
                            ]
                        },
                        "estimatedCost": {
                            "totalAmount": {
                                "amount": str(float(299.00) * quantity),
                                "currencyCode": "CNY"
                            }
                        }
                    },
                    "userErrors": []
                }
            }
        }
    
    def _mock_cart_get_data(self) -> Dict:
        """模拟获取购物车数据"""
        if not self.cart_id:
            return {"data": {"cart": None}}
            
        return {
            "data": {
                "cart": {
                    "id": self.cart_id,
                    "lines": {
                        "edges": [
                            {
                                "node": {
                                    "id": "gid://shopify/CartLine/1",
                                    "quantity": 2,
                                    "merchandise": {
                                        "id": "gid://shopify/ProductVariant/10001",
                                        "title": "S / 白色",
                                        "product": {"title": "亚麻短袖衬衫"},
                                        "price": {"amount": "299.00", "currencyCode": "CNY"}
                                    },
                                    "cost": {
                                        "totalAmount": {
                                            "amount": "598.00",
                                            "currencyCode": "CNY"
                                        }
                                    }
                                }
                            }
                        ]
                    },
                    "estimatedCost": {
                        "subtotalAmount": {"amount": "598.00", "currencyCode": "CNY"},
                        "totalTaxAmount": {"amount": "0.00", "currencyCode": "CNY"},
                        "totalAmount": {"amount": "598.00", "currencyCode": "CNY"}
                    }
                }
            }
        }
    
    # 高级API方法
    async def get_collections(self, first: int = 10) -> Dict:
        """获取商品集合/品类 - 带缓存"""
        cache_key = f"collections_{first}"
        
        if self._is_cache_valid(cache_key, 'collections'):
            logger.info("Returning cached collections")
            return self._get_cache(cache_key)
        
        query = """
        query GetCollections($first: Int!) {
            collections(first: $first) {
                edges {
                    node {
                        id
                        title
                        description
                        handle
                        image {
                            url
                            altText
                        }
                        productsCount
                    }
                }
            }
        }
        """
        variables = {'first': first}
        result = await self.execute_graphql_query(query, variables)
        
        if 'errors' not in result:
            self._set_cache(cache_key, result)
        
        return result
    
    async def search_products(self, query: str, first: int = 10, filters: Optional[Dict] = None) -> Dict:
        """全局商品搜索"""
        cache_key = f"search_{query}_{first}_{hash(str(filters))}"
        
        if self._is_cache_valid(cache_key, 'products'):
            return self._get_cache(cache_key)
        
        # 构建搜索查询
        search_query = f"""
        query SearchProducts($query: String!, $first: Int!) {{
            products(first: $first, query: $query) {{
                edges {{
                    node {{
                        id
                        title
                        description
                        handle
                        priceRange {{
                            minVariantPrice {{
                                amount
                                currencyCode
                            }}
                        }}
                        images(first: 1) {{
                            edges {{
                                node {{
                                    url
                                    altText
                                }}
                            }}
                        }}
                        tags
                        vendor
                        productType
                        availableForSale
                    }}
                }}
            }}
        }}
        """
        
        variables = {'query': query, 'first': first}
        result = await self.execute_graphql_query(search_query, variables)
        
        if 'errors' not in result:
            self._set_cache(cache_key, result)
        
        return result
    
    async def get_products_by_collection(self, collection_id: str, first: int = 10, sort_key: str = "TITLE") -> Dict:
        """获取指定集合中的产品 - 增强版"""
        cache_key = f"collection_products_{collection_id}_{first}_{sort_key}"
        
        if self._is_cache_valid(cache_key, 'products'):
            return self._get_cache(cache_key)
        
        query = f"""
        query GetProductsByCollection($collectionId: ID!, $first: Int!, $sortKey: ProductCollectionSortKeys!) {{
            collection(id: $collectionId) {{
                title
                description
                products(first: $first, sortKey: $sortKey) {{
                    edges {{
                        node {{
                            id
                            title
                            description
                            handle
                            priceRange {{
                                minVariantPrice {{
                                    amount
                                    currencyCode
                                }}
                            }}
                            images(first: 1) {{
                                edges {{
                                    node {{
                                        url
                                        altText
                                    }}
                                }}
                            }}
                            tags
                            vendor
                            productType
                            availableForSale
                        }}
                    }}
                }}
            }}
        }}
        """
        
        variables = {
            'collectionId': collection_id,
            'first': first,
            'sortKey': sort_key
        }
        result = await self.execute_graphql_query(query, variables)
        
        if 'errors' not in result:
            self._set_cache(cache_key, result)
        
        return result
    
    async def get_product_details(self, product_id: str) -> Dict:
        """获取产品详情 - 增强版"""
        cache_key = f"product_details_{product_id}"
        
        if self._is_cache_valid(cache_key, 'product_details'):
            return self._get_cache(cache_key)
        
        query = """
        query GetProductDetails($productId: ID!) {
            product(id: $productId) {
                id
                title
                description
                handle
                availableForSale
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
                images(first: 10) {
                    edges {
                        node {
                            url
                            altText
                        }
                    }
                }
                variants(first: 20) {
                    edges {
                        node {
                            id
                            title
                            price {
                                amount
                                currencyCode
                            }
                            availableForSale
                            selectedOptions {
                                name
                                value
                            }
                        }
                    }
                }
                tags
                vendor
                productType
                options {
                    name
                    values
                }
            }
        }
        """
        variables = {'productId': product_id}
        result = await self.execute_graphql_query(query, variables)
        
        if 'errors' not in result:
            self._set_cache(cache_key, result)
        
        return result
    
    async def create_cart(self, lines: Optional[List[Dict]] = None) -> Dict:
        """创建购物车 - 增强版"""
        mutation = """
        mutation CreateCart($input: CartInput!) {
            cartCreate(input: $input) {
                cart {
                    id
                    checkoutUrl
                    createdAt
                    updatedAt
                    lines(first: 10) {
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
                    estimatedCost {
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
        
        cart_input = {}
        if lines:
            cart_input['lines'] = lines
        
        variables = {'input': cart_input}
        result = await self.execute_graphql_query(mutation, variables)
        
        # 保存购物车ID供后续使用
        if ('data' in result and 'cartCreate' in result['data'] and 
            result['data']['cartCreate']['cart']):
            self.cart_id = result['data']['cartCreate']['cart']['id']
            self.cart_created_at = datetime.now()
        
        return result
    
    async def add_to_cart(self, variant_id: str, quantity: int = 1) -> Dict:
        """添加商品到购物车 - 增强版"""
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
                    lines(first: 20) {
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
                    estimatedCost {
                        subtotalAmount {
                            amount
                            currencyCode
                        }
                        totalTaxAmount {
                            amount
                            currencyCode
                        }
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
            'lines': [
                {
                    'merchandiseId': variant_id,
                    'quantity': quantity
                }
            ]
        }
        
        return await self.execute_graphql_query(mutation, variables)
    
    async def get_cart(self) -> Dict:
        """获取购物车内容 - 增强版"""
        if not self.cart_id:
            return {"data": {"cart": None}}
        
        query = """
        query GetCart($cartId: ID!) {
            cart(id: $cartId) {
                id
                createdAt
                updatedAt
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
                        }
                    }
                }
                estimatedCost {
                    subtotalAmount {
                        amount
                        currencyCode
                    }
                    totalTaxAmount {
                        amount
                        currencyCode
                    }
                    totalAmount {
                        amount
                        currencyCode
                    }
                }
                checkoutUrl
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
                                            title
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
                    estimatedCost {
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
                                            title
                                        }
                                    }
                                }
                            }
                        }
                    }
                    estimatedCost {
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
    
    async def checkout(self) -> Dict:
        """获取结账URL - 增强版"""
        if not self.cart_id:
            return {"error": "No active cart to checkout"}
        
        # 获取当前购物车信息
        cart_info = await self.get_cart()
        
        if ('data' in cart_info and cart_info['data']['cart'] and 
            cart_info['data']['cart']['checkoutUrl']):
            return {
                "success": True,
                "checkout_url": cart_info['data']['cart']['checkoutUrl'],
                "cart_id": self.cart_id,
                "total_amount": cart_info['data']['cart']['estimatedCost']['totalAmount']['amount'],
                "currency": cart_info['data']['cart']['estimatedCost']['totalAmount']['currencyCode']
            }
        else:
            return {
                "success": False,
                "error": "Unable to generate checkout URL"
            }
    
    async def get_product_recommendations(self, product_id: str, intent: str = "RELATED") -> Dict:
        """获取商品推荐"""
        query = """
        query GetProductRecommendations($productId: ID!, $intent: ProductRecommendationIntent!) {
            productRecommendations(productId: $productId, intent: $intent) {
                id
                title
                handle
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
            }
        }
        """
        
        variables = {
            'productId': product_id,
            'intent': intent
        }
        
        return await self.execute_graphql_query(query, variables)
    
    def clear_cache(self) -> None:
        """清理缓存"""
        self.cache.clear()
        logger.info("Cache cleared")
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计"""
        return {
            "total_entries": len(self.cache),
            "cache_keys": list(self.cache.keys()),
            "memory_usage": f"{len(str(self.cache))} characters"
        }encyCode": "CNY"}},
                        "images": {"edges": [{"node": {"url": "https://example.com/images/linen-shirt.jpg", "altText": "亚麻衬衫"}}]},
                        "tags": ["夏季", "透气", "舒适", "商务休闲"]
                    },
                    {
                        "id": "gid://shopify/Product/1002",
                        "title": "棉质短裤",
                        "description": "柔软舒适的纯棉短裤",
                        "handle": "cotton-shorts",
                        "priceRange": {"minVariantPrice": {"amount": "199.00", "currencyCode": "CNY"}},
                        "images": {"edges": [{"node": {"url": "https://example.com/images/cotton-shorts.jpg", "altText": "棉质短裤"}}]},
                        "tags": ["夏季", "舒适", "休闲"]
                    }
                ]
            },
            "gid://shopify/Collection/222": {  # 商务装
                "title": "商务装",
                "products": [
                    {
                        "id": "gid://shopify/Product/2001",
                        "title": "经典西装外套",
                        "description": "修身剪裁的商务西装外套",
                        "handle": "classic-blazer",
                        "priceRange": {"minVariantPrice": {"amount": "899.00", "currencyCode": "CNY"}},
                        "images": {"edges": [{"node": {"url": "https://example.com/images/blazer.jpg", "altText": "西装外套"}}]},
                        "tags": ["商务", "正装", "修身", "经典"]
                    }
                ]
            }
        }
        
        collection_data = products_by_collection.get(collection_id, {
            "title": "默认系列",
            "products": []
        })
        
        return {
            "data": {
                "collection": {
                    "title": collection_data["title"],
                    "products": {
                        "edges": [{"node": product} for product in collection_data["products"]]
                    }
                }
            }
        }
    
    def _mock_search_results(self, query: str) -> Dict:
        """模拟搜索结果"""
        all_products = [
            {
                "id": "gid://shopify/Product/1001",
                "title": "亚麻短袖衬衫",
                "description": "透气舒适的纯亚麻衬衫",
                "handle": "linen-shirt",
                "priceRange": {"minVariantPrice": {"amount": "299.00", "currencyCode": "CNY"}},
                "images": {"edges": [{"node": {"url": "https://example.com/images/linen-shirt.jpg", "altText": "亚麻衬衫"}}]}
            },
            {
                "id": "gid://shopify/Product/2001",
                "title": "经典西装外套",
                "description": "修身剪裁的商务西装外套",
                "handle": "classic-blazer",
                "priceRange": {"minVariantPrice": {"amount": "899.00", "currencyCode": "CNY"}},
                "images": {"edges": [{"node": {"url": "https://example.com/images/blazer.jpg", "altText": "西装外套"}}]}
            }
        ]
        
        # 简单的关键词匹配
        filtered_products = []
        if query:
            query_lower = query.lower()
            for product in all_products:
                if (query_lower in product["title"].lower() or 
                    query_lower in product["description"].lower()):
                    filtered_products.append(product)
        else:
            filtered_products = all_products
        
        return {
            "data": {
                "products": {
                    "edges": [{"node": product} for product in filtered_products]
                }
            }
        }
    
    # 继续保留其他模拟数据方法...
    def _mock_product_details_data(self, product_id: str) -> Dict:
        # 保持原有实现
        return {
            "data": {
                "product": {
                    "id": product_id or "gid://shopify/Product/1001",
                    "title": "亚麻短袖衬衫",
                    "description": "透气舒适的纯亚麻衬衫，适合夏季穿着。采用优质亚麻材质，透气性极佳。",
                    "handle": "linen-shirt",
                    "availableForSale": True,
                    "priceRange": {"minVariantPrice": {"amount": "299.00", "curr