"""
Shopify工具集成示例 - 完全独立版本
直接使用Shopify客户端，不依赖任何相对导入
"""

import os
import json
import sys
import requests
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional

# 加载环境变量
load_dotenv('.env.dev')

class ShopifyClient:
    """Shopify Storefront API客户端"""
    
    def __init__(self):
        # 使用环境变量
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

# 美化打印函数
def pretty_print(data: Dict):
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print("-" * 50)

def main():
    """示例主函数"""
    print("Shopify集成示例运行中...")
    
    # 创建Shopify客户端
    client = ShopifyClient()
    
    # 1. 查询产品集合
    print("\n1. 查询产品集合")
    collections_result = client.get_collections(first=5)
    pretty_print(collections_result)
    
    # 如果没有集合，无法继续测试
    if not collections_result.get('data', {}).get('collections', {}).get('edges'):
        print("未找到产品集合，请确保商店中有产品集合")
        return
    
    # 获取第一个集合ID
    collection_id = collections_result['data']['collections']['edges'][0]['node']['id']
    
    # 2. 查询集合中的产品
    print("\n2. 查询集合中的产品")
    products_result = client.get_products_by_collection(collection_id, first=3)
    pretty_print(products_result)
    
    # 如果没有产品，无法继续测试
    if not products_result.get('data', {}).get('collection', {}).get('products', {}).get('edges'):
        print("未找到产品，请确保集合中有产品")
        return
    
    # 获取第一个产品ID
    product_id = products_result['data']['collection']['products']['edges'][0]['node']['id']
    
    # 3. 查询产品详情
    print("\n3. 查询产品详情")
    product_details = client.get_product_details(product_id)
    pretty_print(product_details)
    
    # 获取第一个变体ID
    if not product_details.get('data', {}).get('product', {}).get('variants', {}).get('edges'):
        print("产品没有变体，无法添加到购物车")
        return
    
    variant_id = product_details['data']['product']['variants']['edges'][0]['node']['id']
    
    # 4. 创建购物车
    print("\n4. 创建购物车")
    cart_result = client.create_cart()
    pretty_print(cart_result)
    
    # 5. 添加产品到购物车
    print("\n5. 添加产品到购物车")
    add_result = client.add_to_cart(variant_id, quantity=1)
    pretty_print(add_result)
    
    # 6. 查看购物车
    print("\n6. 查看购物车")
    view_result = client.get_cart()
    pretty_print(view_result)
    
    # 7. 获取结账URL
    print("\n7. 获取结账URL")
    checkout_result = client.checkout()
    pretty_print(checkout_result)
    
    print("\n完整电商流程演示完成!")
    if "checkoutUrl" in checkout_result:
        print(f"请访问以下URL完成支付: {checkout_result.get('checkoutUrl')}")

if __name__ == "__main__":
    main() 