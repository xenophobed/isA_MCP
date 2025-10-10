#!/usr/bin/env python3
"""
Web Authentication Bridge (Using Vault Service)
Connects web automation to HIL authentication and Vault credential storage

Similar to Composio bridge pattern, but for web service authentication:
- Stores credentials in Vault Service (8214)
- Requests user authorization via HIL (Agent)
- Provides credentials to web automation

Supported Auth Types:
- wallet: MetaMask, Coinbase, WalletConnect
- payment: Stripe, PayPal, Apple Pay
- social: Google, GitHub, Facebook OAuth
- basic_auth: Username/Password
- api_key: API keys
- totp: 2FA codes
"""

import json
import asyncio
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from core.security import get_security_manager, SecurityLevel
from core.logging import get_logger

logger = get_logger(__name__)


class WebAuthBridge:
    """
    Bridge between web automation and HIL authentication using Vault Service

    Architecture:
    1. Web Automation needs credentials → Check Vault Service
    2. If not found → Request via HIL (Agent)
    3. User approves → Store in Vault Service
    4. Return credentials to Web Automation
    """

    def __init__(
        self,
        vault_service_url: str = "http://localhost:8214",
        hil_service_url: str = "http://localhost:8000",
    ):
        self.vault_service_url = vault_service_url
        self.hil_service_url = hil_service_url
        self.registered_tools = {}

        # Supported authentication types (maps to Vault secret_type)
        self.auth_types = {
            "wallet": {
                "vault_type": "blockchain_key",
                "providers": ["metamask", "coinbase", "walletconnect", "phantom"],
                "auth_method": "signature",
                "description": "Cryptocurrency wallet authentication",
                "hil_auth_type": "wallet"
            },
            "payment": {
                "vault_type": "api_key",  # Store payment tokens as api_key
                "providers": ["stripe", "paypal", "applepay", "googlepay"],
                "auth_method": "approval",
                "description": "Payment service authorization",
                "hil_auth_type": "payment"
            },
            "social": {
                "vault_type": "oauth_token",
                "providers": ["google", "github", "facebook", "twitter", "linkedin"],
                "auth_method": "oauth",
                "description": "Social login authentication",
                "hil_auth_type": "oauth"
            },
            "basic_auth": {
                "vault_type": "database_credential",  # Reuse for username/password
                "providers": ["custom"],
                "auth_method": "username_password",
                "description": "Username/password authentication",
                "hil_auth_type": "basic_auth"
            },
            "api_key": {
                "vault_type": "api_key",
                "providers": ["custom"],
                "auth_method": "key",
                "description": "API key authentication",
                "hil_auth_type": "api_key"
            },
            "totp": {
                "vault_type": "custom",
                "providers": ["google_authenticator", "authy"],
                "auth_method": "code",
                "description": "Two-factor authentication (TOTP)",
                "hil_auth_type": "totp"
            }
        }

        logger.info(f"🔐 Web Auth Bridge initialized")
        logger.info(f"🏦 Vault Service: {vault_service_url}")
        logger.info(f"👤 HIL Service: {hil_service_url}")

    async def register_web_auth_tools(self, mcp):
        """Register web authentication tools with MCP (like Composio registration)"""
        logger.info("🌉 Registering Web Authentication tools with MCP...")

        try:
            security_manager = get_security_manager()
        except RuntimeError:
            logger.warning("Security manager not initialized")
            security_manager = None

        # Register management tools
        await self._register_management_tools(mcp, security_manager)

        # Register auth type-specific tools
        await self._register_auth_type_tools(mcp, security_manager)

        logger.info(f"✅ Web Authentication bridge registered {len(self.registered_tools)} tools")

    async def _register_management_tools(self, mcp, security_manager):
        """Register management tools (like composio_connect_app)"""

        # Tool 1: List available auth types
        async def web_auth_list_types() -> str:
            """List all available authentication types for web automation

            Shows all supported authentication methods (wallet, payment, social, etc.)
            with their providers and descriptions.

            Returns:
                JSON with auth types, providers, and descriptions

            Keywords: auth, authentication, list, available, types, wallet, payment, social
            Category: authentication
            """
            try:
                auth_types_info = {}
                for auth_type, info in self.auth_types.items():
                    auth_types_info[auth_type] = {
                        "providers": info["providers"],
                        "method": info["auth_method"],
                        "description": info["description"],
                        "vault_type": info["vault_type"]
                    }

                return json.dumps({
                    "status": "success",
                    "total_types": len(self.auth_types),
                    "auth_types": auth_types_info,
                    "message": f"Found {len(self.auth_types)} authentication types"
                }, indent=2)
            except Exception as e:
                logger.error(f"Failed to list auth types: {e}")
                return json.dumps({"status": "error", "message": str(e)})

        # Tool 2: Connect user credentials (stores in Vault)
        async def web_auth_connect(
            auth_type: str,
            provider: str,
            user_id: str = "default",
            name: str = None,
            description: str = None
        ) -> str:
            """Connect and store user credentials for a web service

            Initiates authentication flow via HIL to securely connect and store
            user's credentials in Vault Service.

            Args:
                auth_type: Type of auth (wallet, payment, social, basic_auth, etc.)
                provider: Specific provider (metamask, stripe, google, etc.)
                user_id: User identifier
                name: Optional credential name
                description: Optional description

            Returns:
                JSON with connection status and vault_id

            Keywords: auth, connect, credentials, wallet, payment, login, store
            Category: authentication
            """
            try:
                # Check if auth type is supported
                if auth_type not in self.auth_types:
                    return json.dumps({
                        "status": "error",
                        "message": f"Auth type '{auth_type}' not supported",
                        "available_types": list(self.auth_types.keys())
                    })

                type_info = self.auth_types[auth_type]

                # Check if provider is supported
                if provider not in type_info["providers"] and "custom" not in type_info["providers"]:
                    return json.dumps({
                        "status": "error",
                        "message": f"Provider '{provider}' not supported for {auth_type}",
                        "available_providers": type_info["providers"]
                    })

                # Request credentials via HIL
                hil_result = await self._request_auth_via_hil(
                    auth_type=auth_type,
                    provider=provider,
                    user_id=user_id,
                    action="connect",
                    context={"name": name, "description": description}
                )

                if hil_result.get("status") != "success":
                    return json.dumps(hil_result, indent=2)

                # Store in Vault Service
                vault_result = await self._store_in_vault(
                    user_id=user_id,
                    auth_type=auth_type,
                    provider=provider,
                    credential_data=hil_result.get("credential_data", {}),
                    name=name or f"{provider} {auth_type}",
                    description=description or f"{provider} credentials for {auth_type}"
                )

                return json.dumps(vault_result, indent=2)

            except Exception as e:
                logger.error(f"Failed to connect auth: {e}")
                return json.dumps({"status": "error", "message": str(e)})

        # Tool 3: List user connections (from Vault)
        async def web_auth_list_connections(user_id: str = "default") -> str:
            """List user's connected authentication services

            Shows all authentication services the user has stored in Vault.

            Args:
                user_id: User identifier

            Returns:
                JSON with connected services from Vault

            Keywords: auth, list, connections, user, credentials, vault
            Category: authentication
            """
            try:
                # Query Vault Service for user's credentials
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.vault_service_url}/api/v1/vault/secrets",
                        headers={"X-User-Id": user_id},
                        params={"page": 1, "page_size": 100}
                    )

                    if response.status_code != 200:
                        return json.dumps({
                            "status": "error",
                            "message": f"Failed to query Vault: {response.status_code}"
                        })

                    vault_data = response.json()
                    secrets = vault_data.get("items", [])

                    # Map vault secrets to auth connections
                    connections = []
                    for secret in secrets:
                        # Determine auth_type from vault secret_type
                        auth_type = self._vault_type_to_auth_type(secret.get("secret_type"))
                        if auth_type:
                            connections.append({
                                "auth_type": auth_type,
                                "provider": secret.get("provider", "unknown"),
                                "name": secret.get("name"),
                                "vault_id": secret.get("vault_id"),
                                "created_at": secret.get("created_at"),
                                "is_active": secret.get("is_active", True),
                                "tags": secret.get("tags", [])
                            })

                    return json.dumps({
                        "status": "success",
                        "user_id": user_id,
                        "count": len(connections),
                        "connections": connections
                    }, indent=2)

            except Exception as e:
                logger.error(f"Failed to list connections: {e}")
                return json.dumps({"status": "error", "message": str(e)})

        # Tool 4: Get specific credential (for web automation use)
        async def web_auth_get_credential(
            auth_type: str,
            provider: str,
            user_id: str = "default"
        ) -> str:
            """Get stored credential for web automation

            Retrieves decrypted credential from Vault for use in web automation.
            If credential doesn't exist, initiates HIL flow to request it.

            Args:
                auth_type: Type of authentication
                provider: Provider name
                user_id: User identifier

            Returns:
                JSON with decrypted credential data

            Keywords: auth, get, credential, decrypt, vault, automation
            Category: authentication
            """
            try:
                credential = await self.get_credentials_for_automation(
                    user_id=user_id,
                    auth_type=auth_type,
                    provider=provider
                )

                if credential:
                    return json.dumps({
                        "status": "success",
                        "credential": credential
                    }, indent=2)
                else:
                    return json.dumps({
                        "status": "error",
                        "message": "Credential not found and HIL authorization failed"
                    })

            except Exception as e:
                logger.error(f"Failed to get credential: {e}")
                return json.dumps({"status": "error", "message": str(e)})

        # Register tools with MCP
        mcp.register_tool(
            "web_auth_list_types",
            web_auth_list_types,
            security_level=SecurityLevel.LOW if security_manager else None
        )
        self.registered_tools["web_auth_list_types"] = True

        mcp.register_tool(
            "web_auth_connect",
            web_auth_connect,
            security_level=SecurityLevel.MEDIUM if security_manager else None
        )
        self.registered_tools["web_auth_connect"] = True

        mcp.register_tool(
            "web_auth_list_connections",
            web_auth_list_connections,
            security_level=SecurityLevel.LOW if security_manager else None
        )
        self.registered_tools["web_auth_list_connections"] = True

        mcp.register_tool(
            "web_auth_get_credential",
            web_auth_get_credential,
            security_level=SecurityLevel.MEDIUM if security_manager else None
        )
        self.registered_tools["web_auth_get_credential"] = True

        logger.info("✅ Registered 4 web auth management tools")

    async def _register_auth_type_tools(self, mcp, security_manager):
        """Register auth type-specific tools (like composio_gmail_send_message)"""

        # For each auth type, create authorize tool
        for auth_type, type_info in self.auth_types.items():

            # Create authorize tool for this auth type
            async def authorize_tool(
                provider: str,
                user_id: str = "default",
                action: str = "authorize",
                context: Dict[str, Any] = None,
                _auth_type=auth_type  # Capture in closure
            ) -> str:
                f"""Authorize {_auth_type} for web automation

                Request user authorization to use {_auth_type} credentials
                during web automation. Triggers HIL approval flow if needed.

                Args:
                    provider: Provider name
                    user_id: User identifier
                    action: Action to authorize (authorize, payment, connect)
                    context: Additional context (amount, url, etc.)

                Returns:
                    JSON with authorization result and credentials

                Keywords: {_auth_type}, authorize, approval, hil, web automation
                Category: authentication
                """
                try:
                    if context is None:
                        context = {}

                    # Get or request credentials
                    credential = await self.get_credentials_for_automation(
                        user_id=user_id,
                        auth_type=_auth_type,
                        provider=provider,
                        action_context=context
                    )

                    if credential:
                        return json.dumps({
                            "status": "success",
                            "authorized": True,
                            "credential": credential,
                            "message": f"{_auth_type} authorized for {provider}"
                        }, indent=2)
                    else:
                        return json.dumps({
                            "status": "error",
                            "authorized": False,
                            "message": f"Failed to authorize {_auth_type} for {provider}"
                        })

                except Exception as e:
                    logger.error(f"Authorization failed: {e}")
                    return json.dumps({"status": "error", "message": str(e)})

            # Register the tool
            tool_name = f"web_auth_{auth_type}_authorize"
            mcp.register_tool(
                tool_name,
                authorize_tool,
                security_level=SecurityLevel.HIGH if security_manager else None
            )
            self.registered_tools[tool_name] = True

            logger.info(f"  ✅ Registered {tool_name}")

    async def _request_auth_via_hil(
        self,
        auth_type: str,
        provider: str,
        user_id: str,
        action: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Request authentication via HIL service (Agent)"""

        if context is None:
            context = {}

        type_info = self.auth_types[auth_type]
        auth_method = type_info["auth_method"]
        hil_auth_type = type_info["hil_auth_type"]

        # Prepare HIL request
        hil_request = {
            "question": f"Authorize {provider} for web automation",
            "context": f"""AUTH_TYPE:{hil_auth_type}
Provider: {provider}
Action: {action}
Method: {auth_method}
Description: {type_info['description']}

Context:
{json.dumps(context, indent=2)}
""",
            "auth_type": hil_auth_type,
            "auth_data": {
                "auth_type": auth_type,
                "provider": provider,
                "action": action,
                "method": auth_method,
                "context": context
            },
            "user_id": user_id,
            "node_source": "web_automation"
        }

        # Call HIL service (Agent)
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.hil_service_url}/api/v1/agents/hil/web_auth",
                    json=hil_request
                )

                if response.status_code == 200:
                    result = response.json()
                    return result
                else:
                    return {
                        "status": "error",
                        "message": f"HIL service error: {response.status_code}",
                        "error_code": "HIL_HTTP_ERROR"
                    }

        except httpx.TimeoutException:
            return {
                "status": "error",
                "message": "HIL request timed out (5 minutes)",
                "error_code": "HIL_TIMEOUT"
            }
        except Exception as e:
            logger.error(f"HIL request failed: {e}")
            return {
                "status": "error",
                "message": f"HIL service error: {str(e)}",
                "error_code": "HIL_ERROR"
            }

    async def _store_in_vault(
        self,
        user_id: str,
        auth_type: str,
        provider: str,
        credential_data: Dict[str, Any],
        name: str,
        description: str
    ) -> Dict[str, Any]:
        """Store credentials in Vault Service"""

        type_info = self.auth_types[auth_type]
        vault_secret_type = type_info["vault_type"]

        # Extract secret value from credential_data
        secret_value = self._extract_secret_value(credential_data)

        if not secret_value:
            return {
                "status": "error",
                "message": "No secret value provided in credential_data"
            }

        # Create secret in Vault
        vault_payload = {
            "secret_type": vault_secret_type,
            "provider": provider,
            "name": name,
            "description": description,
            "secret_value": secret_value,
            "tags": [auth_type, provider, "web_auth"],
            "metadata": {
                "auth_type": auth_type,
                "created_by": "web_auth_bridge",
                "credential_data": credential_data
            }
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.vault_service_url}/api/v1/vault/secrets",
                    headers={
                        "X-User-Id": user_id,
                        "Content-Type": "application/json"
                    },
                    json=vault_payload
                )

                if response.status_code == 200:
                    vault_result = response.json()
                    logger.info(f"✅ Stored credential in Vault: {vault_result.get('vault_id')}")
                    return {
                        "status": "success",
                        "vault_id": vault_result.get("vault_id"),
                        "auth_type": auth_type,
                        "provider": provider,
                        "message": f"Credential stored successfully in Vault"
                    }
                else:
                    error_msg = response.text
                    logger.error(f"Failed to store in Vault: {response.status_code} - {error_msg}")
                    return {
                        "status": "error",
                        "message": f"Failed to store in Vault: {response.status_code}",
                        "error_code": "VAULT_STORE_ERROR"
                    }

        except Exception as e:
            logger.error(f"Vault storage failed: {e}")
            return {
                "status": "error",
                "message": f"Vault service error: {str(e)}",
                "error_code": "VAULT_ERROR"
            }

    async def get_credentials_for_automation(
        self,
        user_id: str,
        auth_type: str,
        provider: str,
        action_context: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get credentials for web automation usage

        This is called by WebAutomationService when it needs credentials.
        Flow:
        1. Check Vault Service for existing credentials
        2. If not found, trigger HIL flow to request from user
        3. Store in Vault and return
        """

        # Step 1: Check Vault for existing credentials
        try:
            async with httpx.AsyncClient() as client:
                # List secrets filtered by provider
                response = await client.get(
                    f"{self.vault_service_url}/api/v1/vault/secrets",
                    headers={"X-User-Id": user_id},
                    params={"tags": f"{auth_type},{provider}"}
                )

                if response.status_code == 200:
                    vault_data = response.json()
                    secrets = vault_data.get("items", [])

                    if secrets:
                        # Found existing credential - get decrypted value
                        vault_id = secrets[0]["vault_id"]
                        secret_response = await client.get(
                            f"{self.vault_service_url}/api/v1/vault/secrets/{vault_id}",
                            headers={"X-User-Id": user_id}
                        )

                        if secret_response.status_code == 200:
                            secret_data = secret_response.json()
                            logger.info(f"✅ Retrieved credential from Vault: {vault_id}")
                            return {
                                "vault_id": vault_id,
                                "provider": provider,
                                "auth_type": auth_type,
                                "secret_value": secret_data.get("secret_value"),
                                "metadata": secret_data.get("metadata", {}),
                                "from_vault": True
                            }

        except Exception as e:
            logger.warning(f"Failed to check Vault: {e}")

        # Step 2: No credentials found - request via HIL
        logger.info(f"No stored credentials, requesting via HIL for {auth_type}/{provider}")

        hil_result = await self._request_auth_via_hil(
            auth_type=auth_type,
            provider=provider,
            user_id=user_id,
            action="authorize",
            context=action_context or {}
        )

        if hil_result.get("status") != "success":
            logger.error(f"HIL authorization failed: {hil_result.get('message')}")
            return None

        # Step 3: Store in Vault
        vault_result = await self._store_in_vault(
            user_id=user_id,
            auth_type=auth_type,
            provider=provider,
            credential_data=hil_result.get("credential_data", {}),
            name=f"{provider} {auth_type}",
            description=f"Authorized via HIL for web automation"
        )

        if vault_result.get("status") == "success":
            return {
                "vault_id": vault_result.get("vault_id"),
                "provider": provider,
                "auth_type": auth_type,
                "credential_data": hil_result.get("credential_data", {}),
                "from_hil": True
            }

        return None

    def _extract_secret_value(self, credential_data: Dict[str, Any]) -> Optional[str]:
        """Extract secret value from credential data"""
        # Try common keys
        for key in ["secret_value", "password", "private_key", "api_key", "token", "wallet_address"]:
            if key in credential_data:
                return str(credential_data[key])

        # Fallback: serialize entire credential_data as JSON
        if credential_data:
            return json.dumps(credential_data)

        return None

    def _vault_type_to_auth_type(self, vault_secret_type: str) -> Optional[str]:
        """Map Vault secret_type back to auth_type"""
        for auth_type, info in self.auth_types.items():
            if info["vault_type"] == vault_secret_type:
                return auth_type
        return None


# Export for easy import
__all__ = ['WebAuthBridge']
