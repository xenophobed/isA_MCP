"""
Shopify tools for e-commerce operations.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

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
async def list_collections(limit: int = 10) -> Dict:
    """
    查询Shopify商店中的所有产品品类/集合
    
    @semantic
    concept: 查询产品品类
    domain: 电商
    type: 读取
    
    @functional
    operation: query
    input: limit:int
    output: Dict
    
    @context
    usage: 查看店铺所有产品集合
    prereq: Shopify API凭证
    constraint: 需要有效的店铺域名
    
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
async def query_products(input_data: ProductQueryInput) -> Dict:
    """
    查询Shopify商店中的产品，可以按集合查询或查询单个产品详情
    
    @semantic
    concept: 查询产品信息
    domain: 电商
    type: 读取
    
    @functional
    operation: query
    input: input_data:ProductQueryInput
    output: Dict
    
    @context
    usage: 查看产品详情或集合中的产品列表
    prereq: Shopify API凭证
    constraint: 需要提供集合ID或产品ID
    
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
async def cart_operations(action: str, input_data: Optional[CartOperationInput] = None) -> Dict:
    """
    执行购物车操作，包括创建购物车、添加产品到购物车、查看购物车
    
    @semantic
    concept: 购物车操作
    domain: 电商
    type: 写入
    
    @functional
    operation: cart
    input: action:str,input_data:CartOperationInput
    output: Dict
    
    @context
    usage: 管理购物车，添加商品，查看购物车
    prereq: Shopify API凭证
    constraint: 添加商品需要先创建购物车
    
    Args:
        action: 要执行的操作，可选值为：create（创建购物车）、add（添加商品）、view（查看购物车）
        input_data: 购物车操作输入数据，添加商品时需要提供
        
    Returns:
        购物车操作结果
    
    Example:
        创建购物车：cart_operations(action="create")
        添加商品：cart_operations(action="add", input_data={"variant_id": "gid://shopify/ProductVariant/12345", "quantity": 2})
        查看购物车：cart_operations(action="view")
    """
    
    if action == "create":
        # 创建一个新购物车
        result = shopify_client.create_cart()
        if 'data' in result and 'cartCreate' in result['data']:
            return {
                "success": True,
                "cart_id": result['data']['cartCreate']['cart']['id'],
                "checkout_url": result['data']['cartCreate']['cart']['checkoutUrl']
            }
        else:
            return {"success": False, "error": "无法创建购物车"}
            
    elif action == "add" and input_data:
        # 添加商品到购物车
        result = shopify_client.add_to_cart(input_data.variant_id, input_data.quantity)
        if 'data' in result and 'cartLinesAdd' in result['data']:
            cart = result['data']['cartLinesAdd']['cart']
            cart_lines = []
            
            for edge in cart['lines']['edges']:
                line = edge['node']
                cart_lines.append({
                    'id': line['id'],
                    'quantity': line['quantity'],
                    'title': line['merchandise']['product']['title'],
                    'variant': line['merchandise']['title']
                })
                
            return {
                "success": True,
                "cart_id": cart['id'],
                "items": cart_lines,
                "subtotal": cart['estimatedCost']['totalAmount']['amount'],
                "currency": cart['estimatedCost']['totalAmount']['currencyCode']
            }
        else:
            return {"success": False, "error": "无法添加商品到购物车"}
            
    elif action == "view":
        # 查看购物车
        result = shopify_client.get_cart()
        if not result or 'data' not in result or 'cart' not in result['data']:
            return {"success": False, "error": "购物车不存在或尚未创建"}
            
        cart = result['data']['cart']
        cart_lines = []
        
        for edge in cart['lines']['edges']:
            line = edge['node']
            cart_lines.append({
                'id': line['id'],
                'quantity': line['quantity'],
                'title': line['merchandise']['product']['title'],
                'variant': line['merchandise']['title'],
                'price': line['cost']['totalAmount']['amount']
            })
            
        return {
            "success": True,
            "cart_id": cart['id'],
            "items": cart_lines,
            "subtotal": cart['estimatedCost']['subtotalAmount']['amount'],
            "tax": cart['estimatedCost']['totalTaxAmount']['amount'],
            "total": cart['estimatedCost']['totalAmount']['amount'],
            "currency": cart['estimatedCost']['totalAmount']['currencyCode']
        }
    else:
        return {"success": False, "error": f"不支持的操作: {action}"}

# 结账工具
async def checkout() -> Dict:
    """
    将当前购物车转换为结账链接
    
    @semantic
    concept: 结账支付
    domain: 电商
    type: 读取
    
    @functional
    operation: checkout
    input: 无
    output: Dict
    
    @context
    usage: 完成购物并支付
    prereq: 购物车中有商品
    constraint: 需要有效的购物车ID
    
    Returns:
        结账URL和购物车信息
    
    Example:
        checkout()
    """
    # 获取购物车信息和结账URL
    cart_info = await cart_operations(action="view")
    
    if not cart_info.get("success"):
        return {"success": False, "error": "无法获取购物车信息"}
    
    # 获取结账URL
    checkout_result = shopify_client.checkout()
    if not checkout_result.get("success"):
        return {"success": False, "error": "无法创建结账链接"}
    
    return {
        "success": True,
        "items": cart_info["items"],
        "total": cart_info["total"],
        "currency": cart_info["currency"],
        "checkout_url": checkout_result["checkout_url"]
    } 