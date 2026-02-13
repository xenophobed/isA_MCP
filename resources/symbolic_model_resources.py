#!/usr/bin/env python3
"""
Symbolic Model Resources for Logical Rules and Entity Relationships
"""

import json
from typing import Dict, List, Any, Set
from mcp.server.fastmcp import FastMCP
from core.logging import get_logger

logger = get_logger(__name__)


class SymbolicModel:
    """Symbolic reasoning model with entities, relationships, and rules"""

    def __init__(self):
        self.entities = {
            "customer": {
                "attributes": ["id", "name", "email", "address", "phone", "status"],
                "relationships": ["buys", "owns", "requests", "pays_for"],
                "description": "A person or organization that purchases products or services",
            },
            "product": {
                "attributes": ["id", "name", "price", "category", "inventory", "description"],
                "relationships": ["belongs_to", "requires", "compatible_with"],
                "description": "An item or service offered for sale",
            },
            "invoice": {
                "attributes": ["id", "date", "amount", "status", "due_date", "items"],
                "relationships": ["issued_to", "contains", "references"],
                "description": "A bill for products or services provided",
            },
            "order": {
                "attributes": ["id", "date", "status", "total", "shipping_address"],
                "relationships": ["placed_by", "contains", "ships_to"],
                "description": "A request to purchase products or services",
            },
            "payment": {
                "attributes": ["id", "amount", "method", "date", "status"],
                "relationships": ["made_by", "for", "processed_by"],
                "description": "Money transferred for goods or services",
            },
        }

        self.rules = {
            "business_logic": [
                {
                    "id": "rule_001",
                    "name": "Order Invoice Generation",
                    "condition": "IF customer places order AND order status = 'confirmed'",
                    "action": "THEN generate invoice for customer",
                    "entities": ["customer", "order", "invoice"],
                    "priority": "high",
                },
                {
                    "id": "rule_002",
                    "name": "Inventory Check",
                    "condition": "IF customer buys product AND product.inventory < order.quantity",
                    "action": "THEN notify_insufficient_inventory AND suggest_alternatives",
                    "entities": ["customer", "product", "order"],
                    "priority": "critical",
                },
                {
                    "id": "rule_003",
                    "name": "Payment Processing",
                    "condition": "IF payment received AND payment.amount = invoice.amount",
                    "action": "THEN mark_invoice_paid AND update_order_status",
                    "entities": ["payment", "invoice", "order"],
                    "priority": "high",
                },
                {
                    "id": "rule_004",
                    "name": "Customer Status Update",
                    "condition": "IF customer total_orders > 10 AND customer.status = 'regular'",
                    "action": "THEN update_customer_status('premium') AND apply_discount(10%)",
                    "entities": ["customer"],
                    "priority": "medium",
                },
            ],
            "validation_rules": [
                {
                    "id": "val_001",
                    "name": "Required Fields",
                    "condition": "IF creating customer",
                    "action": "THEN require(name, email) AND validate_email_format",
                    "entities": ["customer"],
                    "priority": "critical",
                },
                {
                    "id": "val_002",
                    "name": "Price Validation",
                    "condition": "IF creating product",
                    "action": "THEN require(price > 0) AND validate_currency_format",
                    "entities": ["product"],
                    "priority": "high",
                },
            ],
        }

        self.relationships = {
            "customer_buys_product": {
                "source": "customer",
                "target": "product",
                "type": "action",
                "properties": ["quantity", "date", "price_paid"],
            },
            "order_contains_product": {
                "source": "order",
                "target": "product",
                "type": "composition",
                "properties": ["quantity", "unit_price"],
            },
            "invoice_issued_to_customer": {
                "source": "invoice",
                "target": "customer",
                "type": "association",
                "properties": ["issue_date", "due_date"],
            },
        }


class SymbolicReasoner:
    """Symbolic reasoning engine for applying rules and relationships"""

    def __init__(self, model: SymbolicModel = None):
        self.model = model or SymbolicModel()

    def get_relevant_rules(self, entities: List[str], context: str = "") -> List[Dict]:
        """Get rules relevant to the given entities and context"""
        relevant_rules = []

        # Check business logic rules
        for rule in self.model.rules["business_logic"]:
            if any(entity in rule["entities"] for entity in entities):
                relevant_rules.append({"category": "business_logic", **rule})

        # Check validation rules
        for rule in self.model.rules["validation_rules"]:
            if any(entity in rule["entities"] for entity in entities):
                relevant_rules.append({"category": "validation", **rule})

        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        relevant_rules.sort(key=lambda x: priority_order.get(x["priority"], 3))

        return relevant_rules

    def generate_reasoning_context(self, entities: List[str], scenario: str = "") -> str:
        """Generate reasoning context for prompts"""
        relevant_rules = self.get_relevant_rules(entities)

        context = f"## Symbolic Reasoning Context\n\n"
        context += f"**Scenario**: {scenario}\n" if scenario else ""
        context += f"**Entities Involved**: {', '.join(entities)}\n\n"

        if relevant_rules:
            context += "**Applicable Rules**:\n"
            for rule in relevant_rules:
                context += f"- **{rule['name']}** ({rule['priority']} priority)\n"
                context += f"  - Condition: {rule['condition']}\n"
                context += f"  - Action: {rule['action']}\n\n"

        # Add entity definitions
        context += "**Entity Definitions**:\n"
        for entity in entities:
            if entity in self.model.entities:
                entity_info = self.model.entities[entity]
                context += f"- **{entity}**: {entity_info['description']}\n"
                context += f"  - Attributes: {', '.join(entity_info['attributes'])}\n"

        return context

    def extract_entities_from_text(self, text: str) -> List[str]:
        """Extract mentioned entities from text"""
        text_lower = text.lower()
        found_entities = []

        for entity_name in self.model.entities.keys():
            if entity_name in text_lower:
                found_entities.append(entity_name)

        return found_entities


def register_symbolic_model_resources(mcp: FastMCP):
    """Register symbolic model resources with MCP server"""

    @mcp.resource("symbolic://entities/catalog")
    def get_entities_catalog() -> str:
        """
        Get catalog of all symbolic entities and their definitions

        This resource provides the complete catalog of entities
        in the symbolic model with attributes and relationships.

        Keywords: symbolic, entities, catalog, definitions, attributes, model
        Category: reasoning
        """
        model = SymbolicModel()
        return json.dumps(
            {
                "description": "Symbolic Entities Catalog",
                "entities": model.entities,
                "entity_count": len(model.entities),
                "usage": "Reference for understanding business entities and their properties",
            },
            indent=2,
        )

    @mcp.resource("symbolic://rules/business")
    def get_business_rules() -> str:
        """
        Get business logic rules for symbolic reasoning

        This resource provides logical rules that govern business
        processes and entity interactions.

        Keywords: symbolic, rules, business, logic, reasoning, processes
        Category: reasoning
        """
        model = SymbolicModel()
        return json.dumps(
            {
                "description": "Business Logic Rules",
                "rules": model.rules["business_logic"],
                "rule_count": len(model.rules["business_logic"]),
                "usage": "Apply these rules when reasoning about business processes",
            },
            indent=2,
        )

    @mcp.resource("symbolic://rules/validation")
    def get_validation_rules() -> str:
        """
        Get validation rules for data integrity and constraints

        This resource provides validation rules that ensure
        data consistency and business constraints.

        Keywords: symbolic, validation, rules, constraints, integrity, data
        Category: reasoning
        """
        model = SymbolicModel()
        return json.dumps(
            {
                "description": "Validation Rules",
                "rules": model.rules["validation_rules"],
                "rule_count": len(model.rules["validation_rules"]),
                "usage": "Apply these rules when validating data and operations",
            },
            indent=2,
        )

    @mcp.resource("symbolic://relationships/mapping")
    def get_relationships_mapping() -> str:
        """
        Get entity relationship mappings and connections

        This resource provides the mapping of relationships
        between different entities in the symbolic model.

        Keywords: symbolic, relationships, mapping, connections, associations
        Category: reasoning
        """
        model = SymbolicModel()
        return json.dumps(
            {
                "description": "Entity Relationships Mapping",
                "relationships": model.relationships,
                "relationship_count": len(model.relationships),
                "usage": "Understand how entities relate to each other",
            },
            indent=2,
        )

    @mcp.resource("symbolic://reasoning/context")
    def get_reasoning_context() -> str:
        """
        Get comprehensive symbolic reasoning context for prompts

        This resource provides a complete reasoning context
        including entities, rules, and relationships for AI prompts.

        Keywords: symbolic, reasoning, context, prompts, comprehensive, ai
        Category: reasoning
        """
        reasoner = SymbolicReasoner()

        # Example context generation
        sample_entities = ["customer", "order", "invoice"]
        sample_scenario = "Customer places an order and needs invoice generation"

        context = reasoner.generate_reasoning_context(sample_entities, sample_scenario)

        return json.dumps(
            {
                "description": "Symbolic Reasoning Context",
                "sample_context": context,
                "sample_entities": sample_entities,
                "sample_scenario": sample_scenario,
                "usage": "Include this context in prompts for symbolic reasoning",
            },
            indent=2,
        )

    # Registration complete
