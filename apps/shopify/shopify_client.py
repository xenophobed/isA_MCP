"""
Shopify Storefront API客户端
提供与Shopify商店交互的API封装
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from unittest.mock import Mock

# 设置日志
logger = logging.getLogger(__name__)

class ShopifyClient:
    """Shopify Storefront API客户端"""
    
    def __init__(self):
        # 使用环境变量或默认值
        self.store_domain = os.getenv('SHOPIFY_STORE_DOMAIN', 'example.myshopify.com')
        self.storefront_token = os.getenv('SHOPIFY_STOREFRONT_ACCESS_TOKEN', 'dummy_token')
        self.api_version = os.getenv('SHOPIFY_API_VERSION', '2023-10')
        self.storefront_api_url = f"https://{self.store_domain}/api/{self.api_version}/graphql.json"
        self.headers = {
            'Content-Type': 'application/json',
            'X-Shopify-Storefront-Access-Token': self.storefront_token
        }
        # 购物车会话
        self.cart_id = None
        # 是否使用模拟数据
        self.use_mock = True
        
    def execute_query(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """执行GraphQL查询"""
        if self.use_mock:
            logger.info(f"使用模拟数据执行查询")
            return self._get_mock_data(query, variables)
            
        # 真实API调用（当use_mock=False时）
        try:
            import requests
            payload = {
                'query': query,
                'variables': variables or {}
            }
            
            response = requests.post(
                self.storefront_api_url,
                headers=self.headers,
                data=json.dumps(payload)
            )
            
            if response.status_code != 200:
                logger.error(f"查询失败: {response.status_code} {response.text}")
                return {"errors": [{"message": f"API请求失败: {response.status_code}"}]}
                
            return response.json()
        except Exception as e:
            logger.error(f"执行查询时出错: {str(e)}")
            return {"errors": [{"message": f"请求错误: {str(e)}"}]}
    
    def _get_mock_data(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """根据查询类型返回模拟数据"""
        if "GetCollections" in query:
            return self._mock_collections_data()
        elif "GetProductsByCollection" in query:
            return self._mock_products_by_collection_data(variables.get('collectionId'))
        elif "GetProductDetails" in query:
            return self._mock_product_details_data(variables.get('productId'))
        elif "cartCreate" in query:
            return self._mock_cart_create_data()
        elif "cartLinesAdd" in query:
            return self._mock_cart_add_data(variables)
        elif "cart" in query:
            return self._mock_cart_get_data()
        else:
            return {"data": {}}
            
    def _mock_collections_data(self) -> Dict:
        """模拟集合数据"""
        return {
            "data": {
                "collections": {
                    "edges": [
                        {
                            "node": {
                                "id": "gid://shopify/Collection/111",
                                "title": "夏季系列",
                                "description": "2023夏季最新系列产品",
                                "handle": "summer-collection",
                                "image": {"url": "https://example.com/images/summer.jpg", "altText": "夏季系列图片"}
                            }
                        },
                        {
                            "node": {
                                "id": "gid://shopify/Collection/222",
                                "title": "冬季系列",
                                "description": "2023冬季保暖系列",
                                "handle": "winter-collection",
                                "image": {"url": "https://example.com/images/winter.jpg", "altText": "冬季系列图片"}
                            }
                        }
                    ]
                }
            }
        }
    
    def _mock_products_by_collection_data(self, collection_id: str) -> Dict:
        """模拟集合中的产品数据"""
        return {
            "data": {
                "collection": {
                    "title": "夏季系列" if collection_id == "gid://shopify/Collection/111" else "冬季系列",
                    "products": {
                        "edges": [
                            {
                                "node": {
                                    "id": "gid://shopify/Product/1001",
                                    "title": "夏季T恤",
                                    "description": "轻薄透气的纯棉T恤",
                                    "handle": "summer-tshirt",
                                    "priceRange": {
                                        "minVariantPrice": {
                                            "amount": "99.00",
                                            "currencyCode": "CNY"
                                        }
                                    },
                                    "images": {
                                        "edges": [
                                            {
                                                "node": {
                                                    "url": "https://example.com/images/tshirt.jpg",
                                                    "altText": "T恤图片"
                                                }
                                            }
                                        ]
                                    }
                                }
                            },
                            {
                                "node": {
                                    "id": "gid://shopify/Product/1002",
                                    "title": "休闲短裤",
                                    "description": "舒适耐穿的休闲短裤",
                                    "handle": "casual-shorts",
                                    "priceRange": {
                                        "minVariantPrice": {
                                            "amount": "129.00",
                                            "currencyCode": "CNY"
                                        }
                                    },
                                    "images": {
                                        "edges": [
                                            {
                                                "node": {
                                                    "url": "https://example.com/images/shorts.jpg",
                                                    "altText": "短裤图片"
                                                }
                                            }
                                        ]
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
    
    def _mock_product_details_data(self, product_id: str) -> Dict:
        """模拟产品详情数据"""
        return {
            "data": {
                "product": {
                    "id": product_id,
                    "title": "夏季T恤" if product_id == "gid://shopify/Product/1001" else "休闲短裤",
                    "description": "轻薄透气的纯棉T恤，适合夏季穿着",
                    "handle": "summer-tshirt",
                    "availableForSale": True,
                    "priceRange": {
                        "minVariantPrice": {
                            "amount": "99.00",
                            "currencyCode": "CNY"
                        }
                    },
                    "images": {
                        "edges": [
                            {
                                "node": {
                                    "url": "https://example.com/images/tshirt1.jpg",
                                    "altText": "T恤正面图"
                                }
                            },
                            {
                                "node": {
                                    "url": "https://example.com/images/tshirt2.jpg",
                                    "altText": "T恤背面图"
                                }
                            }
                        ]
                    },
                    "variants": {
                        "edges": [
                            {
                                "node": {
                                    "id": "gid://shopify/ProductVariant/10001",
                                    "title": "S / 白色",
                                    "price": {
                                        "amount": "99.00",
                                        "currencyCode": "CNY"
                                    },
                                    "availableForSale": True
                                }
                            },
                            {
                                "node": {
                                    "id": "gid://shopify/ProductVariant/10002",
                                    "title": "M / 白色",
                                    "price": {
                                        "amount": "99.00",
                                        "currencyCode": "CNY"
                                    },
                                    "availableForSale": True
                                }
                            },
                            {
                                "node": {
                                    "id": "gid://shopify/ProductVariant/10003",
                                    "title": "L / 白色",
                                    "price": {
                                        "amount": "99.00",
                                        "currencyCode": "CNY"
                                    },
                                    "availableForSale": True
                                }
                            }
                        ]
                    }
                }
            }
        }
    
    def _mock_cart_create_data(self) -> Dict:
        """模拟创建购物车数据"""
        self.cart_id = "gid://shopify/Cart/abc123"
        return {
            "data": {
                "cartCreate": {
                    "cart": {
                        "id": self.cart_id,
                        "checkoutUrl": "https://example.myshopify.com/cart/abc123"
                    },
                    "userErrors": []
                }
            }
        }
    
    def _mock_cart_add_data(self, variables: Dict) -> Dict:
        """模拟添加商品到购物车数据"""
        if not self.cart_id:
            return self._mock_cart_create_data()
            
        variant_id = variables.get('lines', [{}])[0].get('merchandiseId', '')
        quantity = variables.get('lines', [{}])[0].get('quantity', 1)
        
        return {
            "data": {
                "cartLinesAdd": {
                    "cart": {
                        "id": self.cart_id,
                        "lines": {
                            "edges": [
                                {
                                    "node": {
                                        "id": "gid://shopify/CartLine/1",
                                        "quantity": quantity,
                                        "merchandise": {
                                            "id": variant_id,
                                            "title": "S / 白色",
                                            "product": {
                                                "title": "夏季T恤"
                                            }
                                        }
                                    }
                                }
                            ]
                        },
                        "estimatedCost": {
                            "totalAmount": {
                                "amount": "99.00",
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
                                        "product": {
                                            "title": "夏季T恤"
                                        }
                                    },
                                    "cost": {
                                        "totalAmount": {
                                            "amount": "198.00",
                                            "currencyCode": "CNY"
                                        }
                                    }
                                }
                            }
                        ]
                    },
                    "estimatedCost": {
                        "subtotalAmount": {
                            "amount": "198.00",
                            "currencyCode": "CNY"
                        },
                        "totalTaxAmount": {
                            "amount": "0.00",
                            "currencyCode": "CNY"
                        },
                        "totalAmount": {
                            "amount": "198.00",
                            "currencyCode": "CNY"
                        }
                    }
                }
            }
        }
    
    def get_collections(self, first: int = 10) -> Dict:
        """获取商品集合/品类"""
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
                    }
                }
            }
        }
        """
        variables = {'first': first}
        return self.execute_query(query, variables)
    
    def get_products_by_collection(self, collection_id: str, first: int = 10) -> Dict:
        """获取指定集合中的产品"""
        query = """
        query GetProductsByCollection($collectionId: ID!, $first: Int!) {
            collection(id: $collectionId) {
                title
                products(first: $first) {
                    edges {
                        node {
                            id
                            title
                            description
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
                }
            }
        }
        """
        variables = {
            'collectionId': collection_id,
            'first': first
        }
        return self.execute_query(query, variables)
    
    def get_product_details(self, product_id: str) -> Dict:
        """获取产品详情"""
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
                }
                images(first: 5) {
                    edges {
                        node {
                            url
                            altText
                        }
                    }
                }
                variants(first: 10) {
                    edges {
                        node {
                            id
                            title
                            price {
                                amount
                                currencyCode
                            }
                            availableForSale
                        }
                    }
                }
            }
        }
        """
        variables = {'productId': product_id}
        return self.execute_query(query, variables)
    
    def create_cart(self) -> Dict:
        """创建购物车"""
        query = """
        mutation CreateCart {
            cartCreate {
                cart {
                    id
                    checkoutUrl
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        result = self.execute_query(query)
        # 保存购物车ID供后续使用
        if 'data' in result and 'cartCreate' in result['data'] and result['data']['cartCreate']['cart']:
            self.cart_id = result['data']['cartCreate']['cart']['id']
        return result
    
    def add_to_cart(self, variant_id: str, quantity: int = 1) -> Dict:
        """添加商品到购物车"""
        if not self.cart_id:
            self.create_cart()
            
        query = """
        mutation AddToCart($cartId: ID!, $lines: [CartLineInput!]!) {
            cartLinesAdd(cartId: $cartId, lines: $lines) {
                cart {
                    id
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
        
        variables = {
            'cartId': self.cart_id,
            'lines': [
                {
                    'merchandiseId': variant_id,
                    'quantity': quantity
                }
            ]
        }
        
        return self.execute_query(query, variables)
    
    def get_cart(self) -> Dict:
        """获取购物车内容"""
        if not self.cart_id:
            return {"data": {"cart": None}}
            
        query = """
        query GetCart($cartId: ID!) {
            cart(id: $cartId) {
                id
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
        }
        """
        
        variables = {
            'cartId': self.cart_id
        }
        
        return self.execute_query(query, variables)
    
    def checkout(self) -> Dict:
        """获取结账URL"""
        # 在实际实现中，应该创建结账会话并返回URL
        # 这里简单返回模拟数据
        return {
            "success": True,
            "checkout_url": f"https://{self.store_domain}/checkout/{self.cart_id or 'dummy'}"
        } 