# Shopify集成工具

这个模块提供了与Shopify Storefront API的集成，允许用户查询产品目录、添加商品到购物车并完成支付流程。

## 功能

- 查询产品品类/集合
- 查询产品列表和详细信息
- 创建购物车
- 添加商品到购物车
- 查看购物车内容
- 获取结账URL进行支付

## 安装

1. 确保已安装所需依赖:

```bash
pip install requests python-dotenv pydantic
```

2. 创建`.env.dev`文件并添加Shopify API凭证:

```
# Shopify API credentials
SHOPIFY_STORE_DOMAIN=your-store.myshopify.com
SHOPIFY_STOREFRONT_ACCESS_TOKEN=your_storefront_access_token
SHOPIFY_ADMIN_API_KEY=your_admin_api_key
SHOPIFY_API_VERSION=2023-10
```

## 文件结构

- `shopify_client.py`: Shopify Storefront API客户端
- `shopify_tools.py`: MCP工具实现
- `__init__.py`: 导出工具函数
- `example.py`: 使用示例

## 工具说明

### 1. 查询产品品类

使用`shopify_list_collections`工具查询商店中的产品品类/集合。

```python
result = await client.aexecute("shopify_list_collections", {"limit": 5})
```

### 2. 查询产品

使用`shopify_query_products`工具查询产品。可以查询集合中的产品或单个产品详情。

查询集合中的产品:
```python
result = await client.aexecute(
    "shopify_query_products", 
    {"input_data": {"collection_id": "gid://shopify/Collection/12345", "limit": 3}}
)
```

查询产品详情:
```python
result = await client.aexecute(
    "shopify_query_products", 
    {"input_data": {"product_id": "gid://shopify/Product/12345"}}
)
```

### 3. 购物车操作

使用`shopify_cart_operations`工具执行购物车操作。

创建购物车:
```python
result = await client.aexecute("shopify_cart_operations", {"action": "create"})
```

添加商品到购物车:
```python
result = await client.aexecute(
    "shopify_cart_operations", 
    {
        "action": "add", 
        "input_data": {"variant_id": "gid://shopify/ProductVariant/12345", "quantity": 1}
    }
)
```

查看购物车:
```python
result = await client.aexecute("shopify_cart_operations", {"action": "view"})
```

### 4. 结账

使用`shopify_checkout`工具获取结账URL。

```python
result = await client.aexecute("shopify_checkout", {})
```

## 运行示例

运行示例脚本以测试完整流程:

```bash
python apps/shopify/example.py
```

## 注意事项

1. 在使用前，确保`.env.dev`文件中包含正确的Shopify凭证。
2. 确保商店中有产品和集合。
3. Storefront API需要特定权限，请确保您的Access Token具有适当的权限。 