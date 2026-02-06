"""
Aggregator Service Contracts

This package contains data and logic contracts for the MCP Server Aggregator feature.

Contracts:
- data_contract.py: Pydantic schemas and test data factories
- logic_contract.md: Business rules and specifications
- system_contract.md: API contracts and integration points
"""

from tests.contracts.aggregator.data_contract import (
    # Enums
    ServerTransportType,
    ServerStatus,
    RoutingStrategy,

    # Request Contracts
    ServerRegistrationRequestContract,
    ServerConnectionRequestContract,
    AggregatedSearchRequestContract,
    ToolExecutionRequestContract,

    # Response Contracts
    ServerRecordContract,
    AggregatedToolContract,
    RoutingContextContract,
    AggregatorStateContract,
    ToolExecutionResponseContract,
    ServerHealthContract,

    # Factory
    AggregatorTestDataFactory,

    # Builders
    ServerRegistrationBuilder,
    AggregatedToolBuilder,
)

__all__ = [
    # Enums
    "ServerTransportType",
    "ServerStatus",
    "RoutingStrategy",

    # Request Contracts
    "ServerRegistrationRequestContract",
    "ServerConnectionRequestContract",
    "AggregatedSearchRequestContract",
    "ToolExecutionRequestContract",

    # Response Contracts
    "ServerRecordContract",
    "AggregatedToolContract",
    "RoutingContextContract",
    "AggregatorStateContract",
    "ToolExecutionResponseContract",
    "ServerHealthContract",

    # Factory
    "AggregatorTestDataFactory",

    # Builders
    "ServerRegistrationBuilder",
    "AggregatedToolBuilder",
]
