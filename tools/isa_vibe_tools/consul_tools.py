#!/usr/bin/env python3
"""
Consul Tools for MCP Server

Provides service discovery and configuration access for agents via Consul HTTP API.
This allows agents to check service health, discover endpoints, and read configurations.

Migrated from isA_Vibe/src/agents/mcp_servers/consul_mcp.py

Environment:
    CONSUL_HTTP_ADDR: Consul HTTP address (default: http://localhost:8500)
"""

import json
import os
from typing import Optional

from mcp.server.fastmcp import FastMCP
from core.logging import get_logger
from tools.base_tool import BaseTool

# Optional consul import
try:
    import consul
    CONSUL_AVAILABLE = True
except ImportError:
    CONSUL_AVAILABLE = False
    consul = None

logger = get_logger(__name__)
tools = BaseTool()

# Configuration
CONSUL_ADDR = os.getenv("CONSUL_HTTP_ADDR", "http://localhost:8500")
# Parse host and port from address
if CONSUL_ADDR.startswith("http://"):
    addr_parts = CONSUL_ADDR[7:].split(":")
elif CONSUL_ADDR.startswith("https://"):
    addr_parts = CONSUL_ADDR[8:].split(":")
else:
    addr_parts = CONSUL_ADDR.split(":")

CONSUL_HOST = addr_parts[0]
CONSUL_PORT = int(addr_parts[1]) if len(addr_parts) > 1 else 8500


def get_consul_client() -> "consul.Consul":
    """Get Consul client."""
    if not CONSUL_AVAILABLE:
        raise ImportError("python-consul not installed. Install with: pip install python-consul")
    return consul.Consul(host=CONSUL_HOST, port=CONSUL_PORT)


def register_consul_tools(mcp: FastMCP):
    """Register Consul tools with the MCP server."""

    @mcp.tool()
    async def consul_list_services() -> dict:
        """List all registered services in Consul

        Returns:
            Dict with services list and count
        """
        try:
            c = get_consul_client()
            _, services = c.catalog.services()

            service_list = []
            for svc_name, tags in services.items():
                service_list.append({
                    "name": svc_name,
                    "tags": tags
                })

            return tools.create_response(
                status="success",
                action="consul_list_services",
                data={
                    "services": service_list,
                    "count": len(service_list)
                }
            )

        except Exception as e:
            logger.error(f"Error in consul_list_services: {e}")
            return tools.create_response(
                status="error",
                action="consul_list_services",
                data={},
                error_message=str(e)
            )

    @mcp.tool()
    async def consul_get_service(service_name: str) -> dict:
        """Get detailed information about a specific service

        Args:
            service_name: Name of the service (e.g., 'account_service', 'auth_service')

        Returns:
            Dict with service instances and their details
        """
        try:
            c = get_consul_client()
            _, instances = c.catalog.service(service_name)

            if not instances:
                return tools.create_response(
                    status="error",
                    action="consul_get_service",
                    data={"service_name": service_name},
                    error_message=f"Service '{service_name}' not found"
                )

            service_info = []
            for instance in instances:
                service_info.append({
                    "service_id": instance.get("ServiceID"),
                    "address": instance.get("ServiceAddress") or instance.get("Address"),
                    "port": instance.get("ServicePort"),
                    "tags": instance.get("ServiceTags", []),
                    "meta": instance.get("ServiceMeta", {}),
                    "node": instance.get("Node")
                })

            return tools.create_response(
                status="success",
                action="consul_get_service",
                data={
                    "service_name": service_name,
                    "instances": service_info,
                    "count": len(service_info)
                }
            )

        except Exception as e:
            logger.error(f"Error in consul_get_service: {e}")
            return tools.create_response(
                status="error",
                action="consul_get_service",
                data={"service_name": service_name},
                error_message=str(e)
            )

    @mcp.tool()
    async def consul_health_check(service_name: str) -> dict:
        """Get health status of a service

        Args:
            service_name: Name of the service to check health for

        Returns:
            Dict with overall status and instance health details
        """
        try:
            c = get_consul_client()
            _, health = c.health.service(service_name)

            if not health:
                return tools.create_response(
                    status="success",
                    action="consul_health_check",
                    data={
                        "service": service_name,
                        "status": "not_found",
                        "message": f"Service '{service_name}' not found"
                    }
                )

            health_info = []
            for entry in health:
                checks = entry.get("Checks", [])
                status = "passing"
                for check in checks:
                    if check.get("Status") != "passing":
                        status = check.get("Status", "unknown")
                        break

                health_info.append({
                    "service_id": entry.get("Service", {}).get("ID"),
                    "status": status,
                    "checks": [{
                        "name": chk.get("Name"),
                        "status": chk.get("Status"),
                        "output": chk.get("Output", "")[:200]  # Truncate output
                    } for chk in checks]
                })

            overall_status = "passing" if all(h["status"] == "passing" for h in health_info) else "failing"

            return tools.create_response(
                status="success",
                action="consul_health_check",
                data={
                    "service": service_name,
                    "overall_status": overall_status,
                    "instances": health_info
                }
            )

        except Exception as e:
            logger.error(f"Error in consul_health_check: {e}")
            return tools.create_response(
                status="error",
                action="consul_health_check",
                data={"service_name": service_name},
                error_message=str(e)
            )

    @mcp.tool()
    async def consul_get_service_nodes(service_name: str, passing_only: bool = True) -> dict:
        """Get all nodes (instances) of a service

        Args:
            service_name: Name of the service
            passing_only: Only return healthy instances (default: true)

        Returns:
            Dict with node list and count
        """
        try:
            c = get_consul_client()

            if passing_only:
                _, nodes = c.health.service(service_name, passing=True)
            else:
                _, nodes = c.health.service(service_name)

            node_info = []
            for node in nodes:
                svc = node.get("Service", {})
                node_info.append({
                    "node": node.get("Node", {}).get("Node"),
                    "address": svc.get("Address") or node.get("Node", {}).get("Address"),
                    "port": svc.get("Port"),
                    "service_id": svc.get("ID")
                })

            return tools.create_response(
                status="success",
                action="consul_get_service_nodes",
                data={
                    "service": service_name,
                    "passing_only": passing_only,
                    "nodes": node_info,
                    "count": len(node_info)
                }
            )

        except Exception as e:
            logger.error(f"Error in consul_get_service_nodes: {e}")
            return tools.create_response(
                status="error",
                action="consul_get_service_nodes",
                data={"service_name": service_name},
                error_message=str(e)
            )

    @mcp.tool()
    async def consul_get_kv(key: str, recurse: bool = False) -> dict:
        """Get value from Consul KV store

        Args:
            key: Key path in KV store
            recurse: Recursively get all keys under this path (default: false)

        Returns:
            Dict with key-value data
        """
        try:
            c = get_consul_client()

            if recurse:
                _, data = c.kv.get(key, recurse=True)
            else:
                _, data = c.kv.get(key)

            if data is None:
                return tools.create_response(
                    status="error",
                    action="consul_get_kv",
                    data={"key": key},
                    error_message="Key not found"
                )

            if isinstance(data, list):
                # Recursive result
                kv_items = []
                for item in data:
                    value = item.get("Value")
                    if value:
                        try:
                            value = value.decode("utf-8")
                            # Try to parse as JSON
                            try:
                                value = json.loads(value)
                            except (json.JSONDecodeError, TypeError):
                                pass
                        except (UnicodeDecodeError, AttributeError):
                            value = str(value)
                    kv_items.append({
                        "key": item.get("Key"),
                        "value": value
                    })

                return tools.create_response(
                    status="success",
                    action="consul_get_kv",
                    data={"items": kv_items, "count": len(kv_items)}
                )
            else:
                value = data.get("Value")
                if value:
                    try:
                        value = value.decode("utf-8")
                        try:
                            value = json.loads(value)
                        except (json.JSONDecodeError, TypeError):
                            pass
                    except (UnicodeDecodeError, AttributeError):
                        value = str(value)

                return tools.create_response(
                    status="success",
                    action="consul_get_kv",
                    data={"key": key, "value": value}
                )

        except Exception as e:
            logger.error(f"Error in consul_get_kv: {e}")
            return tools.create_response(
                status="error",
                action="consul_get_kv",
                data={"key": key},
                error_message=str(e)
            )

    @mcp.tool()
    async def consul_list_kv(prefix: str = "") -> dict:
        """List keys in Consul KV store

        Args:
            prefix: Key prefix to list (default: empty for root)

        Returns:
            Dict with list of keys
        """
        try:
            c = get_consul_client()
            _, keys = c.kv.get(prefix, keys=True)

            return tools.create_response(
                status="success",
                action="consul_list_kv",
                data={
                    "prefix": prefix,
                    "keys": keys or [],
                    "count": len(keys) if keys else 0
                }
            )

        except Exception as e:
            logger.error(f"Error in consul_list_kv: {e}")
            return tools.create_response(
                status="error",
                action="consul_list_kv",
                data={"prefix": prefix},
                error_message=str(e)
            )

    @mcp.tool()
    async def consul_get_service_tags(service_name: str) -> dict:
        """Get tags for a service (useful for routing metadata)

        Args:
            service_name: Name of the service

        Returns:
            Dict with unique tags from all instances
        """
        try:
            c = get_consul_client()
            _, instances = c.catalog.service(service_name)

            if not instances:
                return tools.create_response(
                    status="error",
                    action="consul_get_service_tags",
                    data={"service_name": service_name},
                    error_message=f"Service '{service_name}' not found"
                )

            # Collect unique tags from all instances
            all_tags = set()
            for instance in instances:
                tags = instance.get("ServiceTags", [])
                all_tags.update(tags)

            return tools.create_response(
                status="success",
                action="consul_get_service_tags",
                data={
                    "service": service_name,
                    "tags": sorted(list(all_tags))
                }
            )

        except Exception as e:
            logger.error(f"Error in consul_get_service_tags: {e}")
            return tools.create_response(
                status="error",
                action="consul_get_service_tags",
                data={"service_name": service_name},
                error_message=str(e)
            )

    @mcp.tool()
    async def consul_get_service_meta(service_name: str) -> dict:
        """Get metadata for a service (includes API paths, auth requirements)

        Args:
            service_name: Name of the service

        Returns:
            Dict with service metadata
        """
        try:
            c = get_consul_client()
            _, instances = c.catalog.service(service_name)

            if not instances:
                return tools.create_response(
                    status="error",
                    action="consul_get_service_meta",
                    data={"service_name": service_name},
                    error_message=f"Service '{service_name}' not found"
                )

            # Get metadata from first instance (should be same across instances)
            meta = instances[0].get("ServiceMeta", {})

            return tools.create_response(
                status="success",
                action="consul_get_service_meta",
                data={
                    "service": service_name,
                    "meta": meta
                }
            )

        except Exception as e:
            logger.error(f"Error in consul_get_service_meta: {e}")
            return tools.create_response(
                status="error",
                action="consul_get_service_meta",
                data={"service_name": service_name},
                error_message=str(e)
            )

    @mcp.tool()
    async def consul_agent_self() -> dict:
        """Get information about the Consul agent

        Returns:
            Dict with agent config and member info
        """
        try:
            c = get_consul_client()
            agent_info = c.agent.self()

            return tools.create_response(
                status="success",
                action="consul_agent_self",
                data={
                    "config": {
                        "datacenter": agent_info.get("Config", {}).get("Datacenter"),
                        "node_name": agent_info.get("Config", {}).get("NodeName"),
                        "version": agent_info.get("Config", {}).get("Version")
                    },
                    "member": {
                        "name": agent_info.get("Member", {}).get("Name"),
                        "addr": agent_info.get("Member", {}).get("Addr"),
                        "status": agent_info.get("Member", {}).get("Status")
                    }
                }
            )

        except Exception as e:
            logger.error(f"Error in consul_agent_self: {e}")
            return tools.create_response(
                status="error",
                action="consul_agent_self",
                data={},
                error_message=str(e)
            )

    logger.debug("Registered 9 Consul tools")
