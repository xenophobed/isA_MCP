#!/usr/bin/env python3
"""
Sub-services for 3GPP Test Plan Generation
Modular component-based architecture
"""

# Lazy imports to avoid circular dependencies
# Only import when explicitly needed

__all__ = [
    "PicsProcessor",
    "PicsTestSelector",
    "Neo4jGraphRAG",
]

def __getattr__(name):
    """Lazy loading of modules"""
    if name == "PicsProcessor":
        from .processor.pics_processor import PicsProcessor
        return PicsProcessor
    elif name == "PicsTestSelector":
        from .processor.pics_test_selector import PicsTestSelector
        return PicsTestSelector
    elif name == "Neo4jGraphRAG":
        from .store.neo4j_graph_rag import Neo4jGraphRAG
        return Neo4jGraphRAG
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")