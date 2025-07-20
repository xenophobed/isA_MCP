"""
Unit tests for Auth0Service

Tests Auth0 integration functionality including:
- JWT token verification
- User info retrieval
- Management token handling
- Error handling and edge cases
"""

import pytest
from unittest.mock import AsyncMock, patch, Mock
import httpx
import jwt
from datetime import datetime, timedelta

from tools.services.user_service.auth_service import Auth0Service
from tools.services.user_service.models import Auth0UserInfo


class TestAuth0Service:
    """Test suite for Auth0Service class"""

    @pytest.fixture
    def auth_service(self, mock_auth0_config):
        """Auth0 service instance for testing"""
        return Auth0Service(
            domain=mock_auth0_config["domain"],
            audience=mock_auth0_config["audience"],
            client_id=mock_auth0_config["client_id"],
            client_secret=mock_auth0_config["client_secret"]
        )

    @pytest.mark.asyncio
    async def test_verify_token_success(self, auth_service):
        """Test successful token verification"""
        # Mock the JWT verification components
        mock_signing_key = Mock()
        mock_signing_key.key = "test_key"
        
        with patch.object(auth_service.jwks_client, 'get_signing_key_from_jwt', return_value=mock_signing_key), \
             patch('jwt.decode') as mock_jwt_decode:
            
            mock_payload = {
                "sub": "auth0|test123",
                "email": "test@example.com",
                "aud": "https://test-domain.auth0.com/api/v2/",
                "iss": "https://test-domain.auth0.com/",
                "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp())
            }
            mock_jwt_decode.return_value = mock_payload
            
            # Execute
            result = await auth_service.verify_token("valid_jwt_token")
            
            # Assert
            assert result == mock_payload
            mock_jwt_decode.assert_called_once_with(
                "valid_jwt_token",
                "test_key",
                algorithms=["RS256"],
                audience="https://test-domain.auth0.com/api/v2/",
                issuer="https://test-domain.auth0.com/"
            )

    @pytest.mark.asyncio
    async def test_verify_token_invalid_token(self, auth_service):
        """Test token verification with invalid token"""
        mock_signing_key = Mock()
        mock_signing_key.key = "test_key"
        
        with patch.object(auth_service.jwks_client, 'get_signing_key_from_jwt', return_value=mock_signing_key), \
             patch('jwt.decode', side_effect=jwt.InvalidTokenError("Invalid token")):
            
            # Execute and Assert
            with pytest.raises(ValueError, match="Invalid token"):
                await auth_service.verify_token("invalid_token")

    @pytest.mark.asyncio
    async def test_verify_token_expired(self, auth_service):
        """Test token verification with expired token"""
        mock_signing_key = Mock()
        mock_signing_key.key = "test_key"
        
        with patch.object(auth_service.jwks_client, 'get_signing_key_from_jwt', return_value=mock_signing_key), \
             patch('jwt.decode', side_effect=jwt.ExpiredSignatureError("Token expired")):
            
            # Execute and Assert
            with pytest.raises(ValueError, match="Invalid token"):
                await auth_service.verify_token("expired_token")

    @pytest.mark.asyncio
    async def test_get_management_token_success(self, auth_service):
        """Test successful management token retrieval"""
        mock_response_data = {
            "access_token": "mgmt_token_123",
            "expires_in": 3600,
            "token_type": "Bearer"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            # Execute
            result = await auth_service.get_management_token()
            
            # Assert
            assert result == "mgmt_token_123"
            assert auth_service._management_token == "mgmt_token_123"
            assert auth_service._token_expires_at is not None

    @pytest.mark.asyncio
    async def test_get_management_token_cached(self, auth_service):
        """Test management token retrieval from cache"""
        # Setup: Set cached token
        auth_service._management_token = "cached_token"
        auth_service._token_expires_at = datetime.utcnow() + timedelta(hours=1)
        
        # Execute
        result = await auth_service.get_management_token()
        
        # Assert
        assert result == "cached_token"

    @pytest.mark.asyncio
    async def test_get_management_token_no_credentials(self):
        """Test management token retrieval without credentials"""
        auth_service = Auth0Service(
            domain="test-domain.auth0.com",
            audience="https://test-domain.auth0.com/api/v2/"
            # No client_id or client_secret
        )
        
        # Execute and Assert
        with pytest.raises(ValueError, match="Client ID and secret required"):
            await auth_service.get_management_token()

    @pytest.mark.asyncio
    async def test_get_management_token_api_error(self, auth_service):
        """Test management token retrieval with API error"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.text = "Bad Request"
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            # Execute and Assert
            with pytest.raises(ValueError, match="Failed to get management token"):
                await auth_service.get_management_token()

    @pytest.mark.asyncio
    async def test_get_user_info_success(self, auth_service):
        """Test successful user info retrieval"""
        mock_user_data = {
            "user_id": "auth0|test123",
            "email": "test@example.com",
            "name": "Test User",
            "picture": "https://example.com/avatar.jpg",
            "email_verified": True
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_user_data
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            # Execute
            result = await auth_service.get_user_info("auth0|test123", "access_token")
            
            # Assert
            assert isinstance(result, Auth0UserInfo)
            assert result.sub == "auth0|test123"
            assert result.email == "test@example.com"
            assert result.name == "Test User"
            assert result.email_verified is True

    @pytest.mark.asyncio
    async def test_get_user_info_with_management_token(self, auth_service):
        """Test user info retrieval using management token"""
        mock_user_data = {
            "user_id": "auth0|test123",
            "email": "test@example.com",
            "name": "Test User",
            "email_verified": False
        }
        
        # Mock management token retrieval
        with patch.object(auth_service, 'get_management_token', return_value="mgmt_token"), \
             patch('httpx.AsyncClient') as mock_client:
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_user_data
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            # Execute (no access_token provided)
            result = await auth_service.get_user_info("auth0|test123")
            
            # Assert
            assert isinstance(result, Auth0UserInfo)
            assert result.sub == "auth0|test123"

    @pytest.mark.asyncio
    async def test_get_user_info_user_not_found(self, auth_service):
        """Test user info retrieval for non-existent user"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 404
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            # Execute and Assert
            with pytest.raises(ValueError, match="User auth0\\|nonexistent not found"):
                await auth_service.get_user_info("auth0|nonexistent", "access_token")

    @pytest.mark.asyncio
    async def test_get_user_info_api_error(self, auth_service):
        """Test user info retrieval with API error"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            # Execute and Assert
            with pytest.raises(ValueError, match="Failed to fetch user info from Auth0"):
                await auth_service.get_user_info("auth0|test123", "access_token")

    @pytest.mark.asyncio
    async def test_update_user_metadata_success(self, auth_service):
        """Test successful user metadata update"""
        metadata = {"subscription": "pro", "credits": 10000}
        
        with patch.object(auth_service, 'get_management_token', return_value="mgmt_token"), \
             patch('httpx.AsyncClient') as mock_client:
            
            mock_response = Mock()
            mock_response.status_code = 200
            
            mock_client.return_value.__aenter__.return_value.patch = AsyncMock(return_value=mock_response)
            
            # Execute
            result = await auth_service.update_user_metadata("auth0|test123", metadata)
            
            # Assert
            assert result is True

    @pytest.mark.asyncio
    async def test_update_user_metadata_failure(self, auth_service):
        """Test user metadata update failure"""
        metadata = {"subscription": "pro"}
        
        with patch.object(auth_service, 'get_management_token', return_value="mgmt_token"), \
             patch('httpx.AsyncClient') as mock_client:
            
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.text = "Bad Request"
            
            mock_client.return_value.__aenter__.return_value.patch = AsyncMock(return_value=mock_response)
            
            # Execute
            result = await auth_service.update_user_metadata("auth0|test123", metadata)
            
            # Assert
            assert result is False

    @pytest.mark.asyncio
    async def test_create_user_success(self, auth_service):
        """Test successful user creation"""
        user_data = {
            "email": "new@example.com",
            "password": "SecurePass123!",
            "name": "New User"
        }
        
        mock_response_data = {
            "user_id": "auth0|new123",
            "email": "new@example.com",
            "name": "New User"
        }
        
        with patch.object(auth_service, 'get_management_token', return_value="mgmt_token"), \
             patch('httpx.AsyncClient') as mock_client:
            
            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.json.return_value = mock_response_data
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            # Execute
            result = await auth_service.create_user(
                email=user_data["email"],
                password=user_data["password"],
                name=user_data["name"]
            )
            
            # Assert
            assert result == "auth0|new123"

    @pytest.mark.asyncio
    async def test_create_user_with_metadata(self, auth_service):
        """Test user creation with metadata"""
        metadata = {"role": "premium_user"}
        
        with patch.object(auth_service, 'get_management_token', return_value="mgmt_token"), \
             patch('httpx.AsyncClient') as mock_client:
            
            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"user_id": "auth0|new123"}
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            # Execute
            result = await auth_service.create_user(
                email="new@example.com",
                password="SecurePass123!",
                name="New User",
                metadata=metadata
            )
            
            # Assert
            assert result == "auth0|new123"

    @pytest.mark.asyncio
    async def test_create_user_failure(self, auth_service):
        """Test user creation failure"""
        with patch.object(auth_service, 'get_management_token', return_value="mgmt_token"), \
             patch('httpx.AsyncClient') as mock_client:
            
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.text = "Email already exists"
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            # Execute
            result = await auth_service.create_user(
                email="existing@example.com",
                password="SecurePass123!",
                name="New User"
            )
            
            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_delete_user_success(self, auth_service):
        """Test successful user deletion"""
        with patch.object(auth_service, 'get_management_token', return_value="mgmt_token"), \
             patch('httpx.AsyncClient') as mock_client:
            
            mock_response = Mock()
            mock_response.status_code = 204
            
            mock_client.return_value.__aenter__.return_value.delete = AsyncMock(return_value=mock_response)
            
            # Execute
            result = await auth_service.delete_user("auth0|test123")
            
            # Assert
            assert result is True

    @pytest.mark.asyncio
    async def test_delete_user_failure(self, auth_service):
        """Test user deletion failure"""
        with patch.object(auth_service, 'get_management_token', return_value="mgmt_token"), \
             patch('httpx.AsyncClient') as mock_client:
            
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.text = "User not found"
            
            mock_client.return_value.__aenter__.return_value.delete = AsyncMock(return_value=mock_response)
            
            # Execute
            result = await auth_service.delete_user("auth0|nonexistent")
            
            # Assert
            assert result is False

    def test_extract_user_id_from_token_success(self, auth_service):
        """Test successful user ID extraction from token"""
        with patch('jwt.decode') as mock_jwt_decode:
            mock_jwt_decode.return_value = {"sub": "auth0|test123"}
            
            # Execute
            result = auth_service.extract_user_id_from_token("jwt_token")
            
            # Assert
            assert result == "auth0|test123"
            mock_jwt_decode.assert_called_once_with("jwt_token", options={"verify_signature": False})

    def test_extract_user_id_from_token_invalid(self, auth_service):
        """Test user ID extraction from invalid token"""
        with patch('jwt.decode', side_effect=Exception("Invalid token")):
            
            # Execute
            result = auth_service.extract_user_id_from_token("invalid_token")
            
            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_network_error_handling(self, auth_service):
        """Test handling of network errors"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.RequestError("Network error")
            )
            
            # Execute and Assert
            with pytest.raises(ValueError, match="Request error"):
                await auth_service.get_management_token()

    @pytest.mark.asyncio
    async def test_management_token_expiry_handling(self, auth_service):
        """Test handling of expired management tokens"""
        # Setup: Set expired token
        auth_service._management_token = "expired_token"
        auth_service._token_expires_at = datetime.utcnow() - timedelta(minutes=1)
        
        mock_response_data = {
            "access_token": "new_token_123",
            "expires_in": 3600
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            # Execute
            result = await auth_service.get_management_token()
            
            # Assert
            assert result == "new_token_123"
            assert auth_service._management_token == "new_token_123"