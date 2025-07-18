# Shopify Tools Documentation

## Overview

The Shopify Tools module provides a comprehensive set of ecommerce tools for interacting with Shopify stores. Built on the BaseTool architecture, it enables real shopping experiences including product search, cart management, and basic checkout functionality.

## Architecture

### ShopifyToolsManager Class

The `ShopifyToolsManager` extends `BaseTool` and serves as the core manager for all Shopify-related operations:

```python
class ShopifyToolsManager(BaseTool):
    """Shopify ecommerce tools manager for real shopping functionality"""
```

#### Key Components:
- **ShopifyClient**: Handles API communication with Shopify
- **Security Manager**: Manages authentication and security
- **Supabase Client**: Handles database operations for user data and sessions

## Available Tools

### 1. search_products

Search for products in the Shopify store with advanced filtering options.

**Parameters:**
- `query` (str): Search keywords
- `category` (str): Product category filter
- `price_min` (float): Minimum price filter
- `price_max` (float): Maximum price filter
- `sort_by` (str): Sort method (relevance, price_low, price_high, newest)
- `limit` (int): Number of results to return (default: 5)
- `user_id` (str): User identifier (default: "guest")

**Response Structure:**
```json
{
  "status": "success",
  "action": "search_products",
  "data": {
    "products": [
      {
        "id": "product_id",
        "title": "Product Title",
        "description": "Product description...",
        "handle": "product-handle",
        "image_url": "https://...",
        "variant": {
          "id": "variant_id",
          "price": 29.99,
          "currency": "USD",
          "available": true
        },
        "vendor": "Vendor Name",
        "available": true
      }
    ],
    "count": 1,
    "search_params": {
      "query": "search term",
      "category": "electronics",
      "price_range": "$20-$50"
    }
  }
}
```

### 2. get_product_details

Retrieve detailed information about a specific product.

**Parameters:**
- `product_id` (str): The Shopify product ID
- `user_id` (str): User identifier (default: "guest")

**Response Structure:**
```json
{
  "status": "success",
  "action": "get_product_details",
  "data": {
    "product": {
      "id": "product_id",
      "title": "Product Title",
      "description": "Full product description",
      "vendor": "Vendor Name",
      "product_type": "Electronics",
      "available": true,
      "images": [
        {
          "url": "https://...",
          "alt": "Image description"
        }
      ],
      "variants": [
        {
          "id": "variant_id",
          "title": "Variant Title",
          "price": "29.99",
          "currency": "USD",
          "available": true,
          "quantity_available": 10,
          "options": []
        }
      ],
      "price_range": {
        "min": "29.99",
        "max": "29.99",
        "currency": "USD"
      }
    }
  }
}
```

### 3. add_to_cart

Add a product variant to the shopping cart.

**Parameters:**
- `variant_id` (str): The product variant ID to add
- `quantity` (int): Quantity to add (default: 1)
- `user_id` (str): User identifier (default: "guest")

**Response Structure:**
```json
{
  "status": "success",
  "action": "add_to_cart",
  "data": {
    "message": "Added 1 item(s) to cart",
    "cart_summary": {
      "cart_id": "cart_id",
      "total_items": 1,
      "total_amount": "29.99",
      "currency": "USD"
    }
  }
}
```

### 4. view_cart

View the contents of the shopping cart.

**Parameters:**
- `user_id` (str): User identifier (default: "guest")

**Response Structure:**
```json
{
  "status": "success",
  "action": "view_cart",
  "data": {
    "cart": {
      "cart_id": "cart_id",
      "items": [
        {
          "line_id": "line_id",
          "quantity": 2,
          "product": {
            "title": "Product Title",
            "variant_title": "Variant Title",
            "price": "29.99",
            "currency": "USD",
            "image_url": "https://..."
          },
          "line_total": "59.98"
        }
      ],
      "summary": {
        "total_items": 2,
        "subtotal": "59.98",
        "total": "59.98",
        "currency": "USD"
      }
    }
  }
}
```

## Error Handling

All tools return standardized error responses when issues occur:

```json
{
  "status": "error",
  "action": "tool_name",
  "data": {},
  "message": "Error description"
}
```

Common error scenarios:
- **Service Unavailable**: When Shopify client is not initialized
- **Product Not Found**: When requested product doesn't exist
- **Cart Errors**: When cart operations fail
- **API Errors**: When Shopify API returns errors

## Usage Examples

### Basic Product Search

```python
# Search for electronics under $100
result = await search_products(
    query="laptop",
    category="electronics",
    price_max=100.0,
    limit=10
)
```

### Complete Shopping Flow

```python
# 1. Search for products
search_result = await search_products(query="headphones")

# 2. Get detailed product information
product_id = search_result["data"]["products"][0]["id"]
details = await get_product_details(product_id)

# 3. Add to cart
variant_id = details["data"]["product"]["variants"][0]["id"]
cart_result = await add_to_cart(variant_id, quantity=1, user_id="user123")

# 4. View cart
cart_contents = await view_cart(user_id="user123")
```

## Security Features

- **Authentication**: All tools use security manager for access control
- **Input Validation**: Parameters are validated before processing
- **Error Sanitization**: Sensitive information is not exposed in error messages
- **Session Management**: Cart sessions are securely stored in Supabase

## Database Integration

The tools integrate with Supabase for:
- **User Sessions**: Cart data persistence
- **User Profiles**: Customer information storage
- **Order History**: Transaction records (when implemented)

## Testing

Comprehensive test suite available in `test_shopify_tools.py`:

- **Unit Tests**: Individual method testing with mocked dependencies
- **Integration Tests**: Complete workflow testing
- **Error Handling Tests**: Exception and edge case coverage
- **Mock Data**: Realistic Shopify API response simulation

Run tests with:
```bash
python -m pytest test_shopify_tools.py -v
```

## Configuration

### Required Environment Variables

```bash
SHOPIFY_STORE_URL=your-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=your_access_token
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### Dependencies

- `mcp.server.fastmcp`: MCP framework
- `tools.base_tool`: Base tool architecture
- `core.security`: Security management
- `core.logging`: Logging utilities
- `core.database.supabase_client`: Database client
- `tools.services.shopify_service.shopify_client`: Shopify API client

## Performance Considerations

- **Caching**: Product data can be cached to reduce API calls
- **Pagination**: Large result sets are paginated automatically
- **Rate Limiting**: Respects Shopify API rate limits
- **Session Cleanup**: Cart sessions expire automatically

## Future Enhancements

- **Payment Processing**: Full checkout and payment handling
- **Order Management**: Order creation and tracking
- **Inventory Management**: Real-time stock updates
- **Customer Accounts**: Full user profile management
- **Wishlist Support**: Product wishlist functionality
- **Reviews & Ratings**: Product review system

## Troubleshooting

### Common Issues

1. **"Shopping service unavailable"**
   - Check Shopify client configuration
   - Verify API credentials
   - Ensure network connectivity

2. **Empty search results**
   - Verify product availability in store
   - Check search query spelling
   - Review price filters

3. **Cart errors**
   - Ensure variant availability
   - Check quantity limits
   - Verify user session

### Debugging

Enable debug logging:
```python
import logging
logging.getLogger('shopify_tools').setLevel(logging.DEBUG)
```

## API Reference

### Tool Registration

```python
from shopify_tools import register_shopify_tools

# Register all Shopify tools with MCP server
register_shopify_tools(mcp_server)
```

### Manual Tool Usage

```python
from shopify_tools import ShopifyToolsManager

# Create manager instance
manager = ShopifyToolsManager()

# Use tools directly
result = await manager.search_products(query="laptop")
```

## Contributing

When contributing to Shopify Tools:

1. Follow the BaseTool architecture patterns
2. Add comprehensive tests for new features
3. Update documentation for API changes
4. Ensure error handling is consistent
5. Test with real Shopify store data when possible

## License

This module is part of the isA MCP project and follows the same licensing terms.