#!/usr/bin/env python3
"""
Test suite for Shopify Tools
Comprehensive tests for shopify_tools.py functionality
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

# Import the module we're testing
from tools.services.ecommerce_service.shopify_tools import ShopifyToolsManager, register_shopify_tools

class TestShopifyToolsManager:
    """Test cases for ShopifyToolsManager class"""
    
    @pytest.fixture
    def mock_shopify_client(self):
        """Mock Shopify client for testing"""
        mock_client = AsyncMock()
        return mock_client
    
    @pytest.fixture
    def mock_supabase(self):
        """Mock Supabase client for testing"""
        mock_supabase = Mock()
        mock_supabase.client = Mock()
        mock_supabase.client.table = Mock()
        return mock_supabase
    
    @pytest.fixture
    def shopify_manager(self, mock_supabase):
        """Create ShopifyToolsManager instance with mocked dependencies"""
        with patch('tools.services.ecommerce_service.shopify_tools.get_security_manager'), \
             patch('tools.services.ecommerce_service.shopify_tools.get_supabase_client', return_value=mock_supabase), \
             patch('tools.services.ecommerce_service.shopify_tools.ShopifyClient') as mock_client_class:
            
            mock_client_class.return_value = AsyncMock()
            manager = ShopifyToolsManager()
            manager.shopify_client = AsyncMock()
            return manager
    
    @pytest.mark.asyncio
    async def test_search_products_success(self, shopify_manager):
        """Test successful product search"""
        # Mock response data
        mock_response = {
            "data": {
                "products": {
                    "edges": [
                        {
                            "node": {
                                "id": "prod_123",
                                "title": "Test Product",
                                "description": "A test product description",
                                "handle": "test-product",
                                "vendor": "Test Vendor",
                                "availableForSale": True,
                                "images": {
                                    "edges": [
                                        {
                                            "node": {
                                                "url": "https://example.com/image.jpg"
                                            }
                                        }
                                    ]
                                },
                                "variants": {
                                    "edges": [
                                        {
                                            "node": {
                                                "id": "var_123",
                                                "price": {
                                                    "amount": "29.99",
                                                    "currencyCode": "USD"
                                                },
                                                "availableForSale": True
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
        
        shopify_manager.shopify_client.search_products.return_value = mock_response
        
        result = await shopify_manager.search_products(
            query="test",
            category="electronics",
            price_min=20.0,
            price_max=50.0,
            limit=5
        )
        
        # Parse the JSON response
        response_data = json.loads(result)
        
        assert response_data["status"] == "success"
        assert response_data["action"] == "search_products"
        assert len(response_data["data"]["products"]) == 1
        assert response_data["data"]["products"][0]["title"] == "Test Product"
        assert response_data["data"]["products"][0]["variant"]["price"] == 29.99
    
    @pytest.mark.asyncio
    async def test_search_products_no_client(self, shopify_manager):
        """Test search products when Shopify client is unavailable"""
        shopify_manager.shopify_client = None
        
        result = await shopify_manager.search_products(query="test")
        response_data = json.loads(result)
        
        assert response_data["status"] == "error"
        assert "Shopping service unavailable" in response_data["message"]
    
    @pytest.mark.asyncio
    async def test_search_products_exception(self, shopify_manager):
        """Test search products when an exception occurs"""
        shopify_manager.shopify_client.search_products.side_effect = Exception("API Error")
        
        result = await shopify_manager.search_products(query="test")
        response_data = json.loads(result)
        
        assert response_data["status"] == "error"
        assert "API Error" in response_data["message"]
    
    @pytest.mark.asyncio
    async def test_get_product_details_success(self, shopify_manager):
        """Test successful product details retrieval"""
        mock_response = {
            "data": {
                "product": {
                    "id": "prod_123",
                    "title": "Test Product",
                    "description": "Detailed product description",
                    "vendor": "Test Vendor",
                    "productType": "Electronics",
                    "availableForSale": True,
                    "images": {
                        "edges": [
                            {
                                "node": {
                                    "url": "https://example.com/image1.jpg",
                                    "altText": "Product image 1"
                                }
                            }
                        ]
                    },
                    "variants": {
                        "edges": [
                            {
                                "node": {
                                    "id": "var_123",
                                    "title": "Default Title",
                                    "price": {
                                        "amount": "29.99",
                                        "currencyCode": "USD"
                                    },
                                    "availableForSale": True,
                                    "quantityAvailable": 10,
                                    "selectedOptions": []
                                }
                            }
                        ]
                    },
                    "priceRange": {
                        "minVariantPrice": {
                            "amount": "29.99",
                            "currencyCode": "USD"
                        },
                        "maxVariantPrice": {
                            "amount": "29.99",
                            "currencyCode": "USD"
                        }
                    }
                }
            }
        }
        
        shopify_manager.shopify_client.get_product_details.return_value = mock_response
        
        result = await shopify_manager.get_product_details("prod_123")
        response_data = json.loads(result)
        
        assert response_data["status"] == "success"
        assert response_data["data"]["product"]["title"] == "Test Product"
        assert len(response_data["data"]["product"]["images"]) == 1
        assert len(response_data["data"]["product"]["variants"]) == 1
    
    @pytest.mark.asyncio
    async def test_add_to_cart_success(self, shopify_manager):
        """Test successful add to cart"""
        mock_response = {
            "data": {
                "cartLinesAdd": {
                    "userErrors": [],
                    "cart": {
                        "id": "cart_123",
                        "totalQuantity": 1,
                        "cost": {
                            "totalAmount": {
                                "amount": "29.99",
                                "currencyCode": "USD"
                            }
                        }
                    }
                }
            }
        }
        
        shopify_manager.shopify_client.add_to_cart.return_value = mock_response
        shopify_manager._save_cart_session = Mock()
        
        result = await shopify_manager.add_to_cart("var_123", 1, "user_123")
        response_data = json.loads(result)
        
        assert response_data["status"] == "success"
        assert "Added 1 item(s) to cart" in response_data["data"]["message"]
        assert response_data["data"]["cart_summary"]["total_items"] == 1
        shopify_manager._save_cart_session.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_to_cart_with_errors(self, shopify_manager):
        """Test add to cart with user errors"""
        mock_response = {
            "data": {
                "cartLinesAdd": {
                    "userErrors": [{"message": "Product not available"}],
                    "cart": None
                }
            }
        }
        
        shopify_manager.shopify_client.add_to_cart.return_value = mock_response
        
        result = await shopify_manager.add_to_cart("var_123", 1)
        response_data = json.loads(result)
        
        assert response_data["status"] == "error"
        assert "Failed to add item to cart" in response_data["message"]
        assert "errors" in response_data["data"]
    
    @pytest.mark.asyncio
    async def test_view_cart_success(self, shopify_manager):
        """Test successful cart viewing"""
        mock_response = {
            "data": {
                "cart": {
                    "id": "cart_123",
                    "totalQuantity": 2,
                    "lines": {
                        "edges": [
                            {
                                "node": {
                                    "id": "line_123",
                                    "quantity": 2,
                                    "merchandise": {
                                        "product": {
                                            "title": "Test Product"
                                        },
                                        "title": "Default Title",
                                        "price": {
                                            "amount": "29.99",
                                            "currencyCode": "USD"
                                        },
                                        "image": {
                                            "url": "https://example.com/image.jpg"
                                        }
                                    },
                                    "cost": {
                                        "totalAmount": {
                                            "amount": "59.98"
                                        }
                                    }
                                }
                            }
                        ]
                    },
                    "cost": {
                        "subtotalAmount": {
                            "amount": "59.98"
                        },
                        "totalAmount": {
                            "amount": "59.98",
                            "currencyCode": "USD"
                        }
                    }
                }
            }
        }
        
        shopify_manager.shopify_client.get_cart.return_value = mock_response
        
        result = await shopify_manager.view_cart("user_123")
        response_data = json.loads(result)
        
        assert response_data["status"] == "success"
        assert response_data["data"]["cart"]["summary"]["total_items"] == 2
        assert len(response_data["data"]["cart"]["items"]) == 1
    
    @pytest.mark.asyncio
    async def test_view_cart_empty(self, shopify_manager):
        """Test viewing empty cart"""
        mock_response = {"data": {"cart": None}}
        
        shopify_manager.shopify_client.get_cart.return_value = mock_response
        
        result = await shopify_manager.view_cart()
        response_data = json.loads(result)
        
        assert response_data["status"] == "success"
        assert "Cart is empty" in response_data["data"]["message"]
        assert response_data["data"]["cart"]["summary"]["total_items"] == 0
    
    def test_truncate_text(self, shopify_manager):
        """Test text truncation utility"""
        # Test short text
        short_text = "Short text"
        result = shopify_manager._truncate_text(short_text, 50)
        assert result == short_text
        
        # Test long text
        long_text = "This is a very long text that should be truncated at some point"
        result = shopify_manager._truncate_text(long_text, 20)
        assert len(result) <= 23  # 20 + "..."
        assert result.endswith("...")
    
    def test_save_cart_session(self, shopify_manager):
        """Test cart session saving"""
        mock_table = Mock()
        shopify_manager.supabase.client.table.return_value = mock_table
        mock_table.upsert.return_value = mock_table
        mock_table.execute.return_value = Mock()
        
        cart_data = {"id": "cart_123", "items": []}
        shopify_manager._save_cart_session("user_123", "cart_123", cart_data)
        
        shopify_manager.supabase.client.table.assert_called_with('user_sessions')
        mock_table.upsert.assert_called_once()
        mock_table.execute.assert_called_once()

class TestRegisterShopifyTools:
    """Test cases for register_shopify_tools function"""
    
    def test_register_shopify_tools(self):
        """Test that tools are registered correctly"""
        mock_mcp = Mock()
        mock_mcp.tool = Mock(return_value=lambda func: func)
        
        with patch('tools.services.ecommerce_service.shopify_tools.ShopifyToolsManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            
            register_shopify_tools(mock_mcp)
            
            # Verify that tools were registered
            assert mock_mcp.tool.call_count == 4  # 4 tools should be registered
            mock_manager_class.assert_called_once()

class TestIntegration:
    """Integration tests for the complete workflow"""
    
    @pytest.mark.asyncio
    async def test_complete_shopping_workflow(self):
        """Test a complete shopping workflow from search to cart"""
        with patch('tools.services.ecommerce_service.shopify_tools.get_security_manager'), \
             patch('tools.services.ecommerce_service.shopify_tools.get_supabase_client'), \
             patch('tools.services.ecommerce_service.shopify_tools.ShopifyClient') as mock_client_class:
            
            # Mock the client
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Mock search response
            search_response = {
                "data": {
                    "products": {
                        "edges": [
                            {
                                "node": {
                                    "id": "prod_123",
                                    "title": "Test Product",
                                    "description": "Test description",
                                    "handle": "test-product",
                                    "vendor": "Test Vendor",
                                    "availableForSale": True,
                                    "images": {"edges": []},
                                    "variants": {
                                        "edges": [
                                            {
                                                "node": {
                                                    "id": "var_123",
                                                    "price": {"amount": "29.99", "currencyCode": "USD"},
                                                    "availableForSale": True
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
            
            # Mock add to cart response
            add_to_cart_response = {
                "data": {
                    "cartLinesAdd": {
                        "userErrors": [],
                        "cart": {
                            "id": "cart_123",
                            "totalQuantity": 1,
                            "cost": {"totalAmount": {"amount": "29.99", "currencyCode": "USD"}}
                        }
                    }
                }
            }
            
            mock_client.search_products.return_value = search_response
            mock_client.add_to_cart.return_value = add_to_cart_response
            
            # Create manager and test workflow
            manager = ShopifyToolsManager()
            manager.shopify_client = mock_client
            manager._save_cart_session = Mock()
            
            # Step 1: Search for products
            search_result = await manager.search_products(query="test")
            search_data = json.loads(search_result)
            
            assert search_data["status"] == "success"
            assert len(search_data["data"]["products"]) == 1
            
            # Step 2: Add product to cart
            variant_id = search_data["data"]["products"][0]["variant"]["id"]
            cart_result = await manager.add_to_cart(variant_id, 1, "user_123")
            cart_data = json.loads(cart_result)
            
            assert cart_data["status"] == "success"
            assert cart_data["data"]["cart_summary"]["total_items"] == 1

if __name__ == "__main__":
    pytest.main([__file__, "-v"])