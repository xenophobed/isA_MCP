from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from core.tool import tool

from apps.shopify.shopify_client import ShopifyClient

# 创建一个单例客户端实例
shopify_client = ShopifyClient()

class ProductQueryInput(BaseModel):
    """产品查询输入模型"""
    collection_id: Optional[str] = Field(None, description="产品集合ID，如果提供则查询该集合下的产品")
    product_id: Optional[str] = Field(None, description="产品ID，如果提供则查询该产品详情")
    limit: int = Field(10, description="查询结果数量限制", ge=1, le=50)

class CartOperationInput(BaseModel):
    """购物车操作输入模型"""
    variant_id: Optional[str] = Field(None, description="产品变体ID，用于添加到购物车")
    quantity: int = Field(1, description="添加到购物车的数量", ge=1)

# 品类查询工具
@tool("shopify_list_collections", return_direct=True)
def list_collections(limit: int = 10) -> Dict:
    """
    查询Shopify商店中的所有产品品类/集合
    
    Args:
        limit: 返回的最大品类数量，默认为10
        
    Returns:
        包含品类列表的字典
    
    Example:
        list_collections(limit=5)
    """
    result = shopify_client.get_collections(first=limit)
    
    # 简化返回结果格式
    collections = []
    if 'data' in result and 'collections' in result['data']:
        for edge in result['data']['collections']['edges']:
            collections.append({
                'id': edge['node']['id'],
                'title': edge['node']['title'],
                'description': edge['node']['description'],
                'handle': edge['node']['handle'],
                'image': edge['node']['image']['url'] if edge['node'].get('image') else None
            })
    
    return {"collections": collections}

# 产品查询工具
@tool("shopify_query_products", return_direct=True)
def query_products(input_data: ProductQueryInput) -> Dict:
    """
    查询Shopify商店中的产品，可以按集合查询或查询单个产品详情
    
    Args:
        input_data: 包含查询参数的ProductQueryInput对象
        
    Returns:
        包含产品信息的字典
    
    Example:
        查询集合中的产品：query_products(input_data={"collection_id": "gid://shopify/Collection/12345", "limit": 5})
        查询单个产品详情：query_products(input_data={"product_id": "gid://shopify/Product/12345"})
    """
    if input_data.product_id:
        # 查询单个产品详情
        result = shopify_client.get_product_details(input_data.product_id)
        
        if 'data' in result and 'product' in result['data']:
            product = result['data']['product']
            
            # 处理变体
            variants = []
            for edge in product['variants']['edges']:
                variants.append({
                    'id': edge['node']['id'],
                    'title': edge['node']['title'],
                    'price': edge['node']['price']['amount'],
                    'currency': edge['node']['price']['currencyCode'],
                    'available': edge['node']['availableForSale']
                })
            
            # 处理图片
            images = []
            for edge in product['images']['edges']:
                images.append({
                    'url': edge['node']['url'],
                    'alt': edge['node']['altText']
                })
            
            return {
                'product': {
                    'id': product['id'],
                    'title': product['title'],
                    'description': product['description'],
                    'handle': product['handle'],
                    'available': product['availableForSale'],
                    'price': product['priceRange']['minVariantPrice']['amount'],
                    'currency': product['priceRange']['minVariantPrice']['currencyCode'],
                    'images': images,
                    'variants': variants
                }
            }
        else:
            return {"error": "产品未找到"}
    
    elif input_data.collection_id:
        # 查询集合中的产品
        result = shopify_client.get_products_by_collection(
            input_data.collection_id, 
            first=input_data.limit
        )
        
        products = []
        if 'data' in result and 'collection' in result['data']:
            collection = result['data']['collection']
            
            for edge in collection['products']['edges']:
                product = edge['node']
                
                # 获取产品图片
                image_url = None
                if product['images']['edges']:
                    image_url = product['images']['edges'][0]['node']['url']
                
                products.append({
                    'id': product['id'],
                    'title': product['title'],
                    'description': product['description'],
                    'handle': product['handle'],
                    'price': product['priceRange']['minVariantPrice']['amount'],
                    'currency': product['priceRange']['minVariantPrice']['currencyCode'],
                    'image': image_url
                })
            
            return {
                'collection': {
                    'title': collection['title'],
                    'products': products
                }
            }
        else:
            return {"error": "集合未找到"}
    
    else:
        return {"error": "必须提供collection_id或product_id"}

# 购物车操作工具
@tool("shopify_cart_operations", return_direct=True)
def cart_operations(action: str, input_data: Optional[CartOperationInput] = None) -> Dict:
    """
    执行购物车操作，包括创建购物车、添加产品到购物车、查看购物车
    
    Args:
        action: 操作类型，可选值："create"、"add"、"view"
        input_data: 操作参数，添加商品时需要提供
        
    Returns:
        操作结果字典
    
    Example:
        创建购物车：cart_operations(action="create")
        添加商品：cart_operations(action="add", input_data={"variant_id": "gid://shopify/ProductVariant/12345", "quantity": 2})
        查看购物车：cart_operations(action="view")
    """
    if action == "create":
        result = shopify_client.create_cart()
        if 'data' in result and 'cartCreate' in result['data']:
            cart = result['data']['cartCreate']['cart']
            return {
                'cart_id': cart['id'],
                'checkout_url': cart['checkoutUrl']
            }
        else:
            return {"error": "创建购物车失败"}
    
    elif action == "add":
        if not input_data or not input_data.variant_id:
            return {"error": "添加商品需要提供variant_id"}
        
        result = shopify_client.add_to_cart(
            input_data.variant_id,
            quantity=input_data.quantity
        )
        
        if 'data' in result and 'cartLinesAdd' in result['data']:
            cart = result['data']['cartLinesAdd']['cart']
            
            # 简化购物车内容
            items = []
            for edge in cart['lines']['edges']:
                item = edge['node']
                merchandise = item['merchandise']
                items.append({
                    'id': item['id'],
                    'quantity': item['quantity'],
                    'variant_id': merchandise['id'],
                    'variant_title': merchandise['title'],
                    'product_title': merchandise['product']['title']
                })
            
            return {
                'cart_id': cart['id'],
                'items': items,
                'total': cart['estimatedCost']['totalAmount']['amount'],
                'currency': cart['estimatedCost']['totalAmount']['currencyCode'],
                'checkout_url': cart['checkoutUrl']
            }
        else:
            return {"error": "添加商品失败"}
    
    elif action == "view":
        result = shopify_client.get_cart()
        
        if 'data' in result and 'cart' in result['data'] and result['data']['cart']:
            cart = result['data']['cart']
            
            # 简化购物车内容
            items = []
            for edge in cart['lines']['edges']:
                item = edge['node']
                merchandise = item['merchandise']
                items.append({
                    'id': item['id'],
                    'quantity': item['quantity'],
                    'variant_id': merchandise['id'],
                    'variant_title': merchandise['title'],
                    'product_title': merchandise['product']['title'],
                    'price': merchandise.get('priceV2', {}).get('amount'),
                    'currency': merchandise.get('priceV2', {}).get('currencyCode')
                })
            
            return {
                'cart_id': cart['id'],
                'items': items,
                'total': cart['estimatedCost']['totalAmount']['amount'],
                'currency': cart['estimatedCost']['totalAmount']['currencyCode'],
                'checkout_url': cart['checkoutUrl']
            }
        else:
            return {"error": "购物车为空或不存在"}
    
    else:
        return {"error": f"不支持的操作: {action}"}

# 结账工具
@tool("shopify_checkout", return_direct=True)
def checkout() -> Dict:
    """
    获取Shopify结账URL，用于完成支付
    
    Returns:
        包含结账URL的字典
    
    Example:
        checkout()
    """
    return shopify_client.checkout() 