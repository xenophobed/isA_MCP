import os
import json
import requests
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional

# 加载环境变量
load_dotenv('.env.dev')

class ShopifyClient:
    """Shopify Storefront API客户端"""
    
    def __init__(self):
        # 使用用户提供的环境变量名称
        self.store_domain = os.getenv('SHOPIFY_STORE_DOMAIN')
        self.storefront_token = os.getenv('SHOPIFY_STOREFRONT_ACCESS_TOKEN')
        self.admin_api_key = os.getenv('SHOPIFY_ADMIN_API_KEY')
        self.api_version = os.getenv('SHOPIFY_API_VERSION', '2023-10')
        self.storefront_api_url = f"https://{self.store_domain}/api/{self.api_version}/graphql.json"
        self.headers = {
            'Content-Type': 'application/json',
            'X-Shopify-Storefront-Access-Token': self.storefront_token
        }
        # 购物车会话
        self.cart_id = None
        
    def execute_query(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """执行GraphQL查询"""
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
            raise Exception(f"查询失败: {response.status_code} {response.text}")
            
        return response.json()
    
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
                    checkoutUrl
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
                    'quantity': quantity,
                    'merchandiseId': variant_id
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
                                    priceV2 {
                                        amount
                                        currencyCode
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
                checkoutUrl
            }
        }
        """
        variables = {'cartId': self.cart_id}
        return self.execute_query(query, variables)
    
    def checkout(self) -> Dict:
        """获取结账URL"""
        if not self.cart_id:
            return {"error": "购物车为空"}
            
        cart_data = self.get_cart()
        if 'data' in cart_data and 'cart' in cart_data['data'] and cart_data['data']['cart']:
            return {"checkoutUrl": cart_data['data']['cart']['checkoutUrl']}
        else:
            return {"error": "无法获取结账链接"} 