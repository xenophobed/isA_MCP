#!/usr/bin/env python3
"""
Graph Analysis and Processing Utilities

Utilities for analyzing and processing graph structures.
"""

import json
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict, deque
import math

from core.logging import get_logger

logger = get_logger(__name__)

def calculate_centrality(graph: Dict[str, Any], 
                        centrality_type: str = "degree",
                        normalize: bool = True) -> Dict[str, float]:
    """
    Calculate centrality measures for graph nodes.
    
    Args:
        graph: Graph structure with 'nodes' and 'edges'
        centrality_type: Type of centrality ("degree", "betweenness", "closeness")
        normalize: Whether to normalize values
        
    Returns:
        Dictionary mapping node IDs to centrality scores
    """
    nodes = graph.get("nodes", {})
    edges = graph.get("edges", {})
    
    if not nodes:
        return {}
    
    # Build adjacency list
    adjacency = defaultdict(set)
    for edge in edges.values():
        source = edge.get("source_id") or edge.get("source")
        target = edge.get("target_id") or edge.get("target")
        if source and target:
            adjacency[source].add(target)
            adjacency[target].add(source)
    
    if centrality_type == "degree":
        return _degree_centrality(nodes, adjacency, normalize)
    elif centrality_type == "betweenness":
        return _betweenness_centrality(nodes, adjacency, normalize)
    elif centrality_type == "closeness":
        return _closeness_centrality(nodes, adjacency, normalize)
    else:
        raise ValueError(f"Unknown centrality type: {centrality_type}")

def _degree_centrality(nodes: Dict[str, Any], 
                      adjacency: Dict[str, Set[str]], 
                      normalize: bool) -> Dict[str, float]:
    """Calculate degree centrality"""
    centrality = {}
    max_degree = len(nodes) - 1 if normalize and len(nodes) > 1 else 1
    
    for node_id in nodes:
        degree = len(adjacency.get(node_id, set()))
        centrality[node_id] = degree / max_degree if normalize else degree
    
    return centrality

def _betweenness_centrality(nodes: Dict[str, Any], 
                           adjacency: Dict[str, Set[str]], 
                           normalize: bool) -> Dict[str, float]:
    """Calculate betweenness centrality using Brandes algorithm"""
    centrality = {node_id: 0.0 for node_id in nodes}
    
    for source in nodes:
        # Single-source shortest paths
        stack = []
        paths = defaultdict(list)
        sigma = defaultdict(int)
        sigma[source] = 1
        distances = {source: 0}
        queue = deque([source])
        
        while queue:
            vertex = queue.popleft()
            stack.append(vertex)
            
            for neighbor in adjacency.get(vertex, set()):
                # Path discovery
                if neighbor not in distances:
                    queue.append(neighbor)
                    distances[neighbor] = distances[vertex] + 1
                
                # Path counting
                if distances[neighbor] == distances[vertex] + 1:
                    sigma[neighbor] += sigma[vertex]
                    paths[neighbor].append(vertex)
        
        # Accumulation
        delta = defaultdict(float)
        while stack:
            vertex = stack.pop()
            for predecessor in paths[vertex]:
                delta[predecessor] += (sigma[predecessor] / sigma[vertex]) * (1 + delta[vertex])
            if vertex != source:
                centrality[vertex] += delta[vertex]
    
    # Normalize
    if normalize and len(nodes) > 2:
        normalization = 2.0 / ((len(nodes) - 1) * (len(nodes) - 2))
        for node_id in centrality:
            centrality[node_id] *= normalization
    
    return centrality

def _closeness_centrality(nodes: Dict[str, Any], 
                         adjacency: Dict[str, Set[str]], 
                         normalize: bool) -> Dict[str, float]:
    """Calculate closeness centrality"""
    centrality = {}
    
    for node_id in nodes:
        # Single-source shortest paths using BFS
        distances = {node_id: 0}
        queue = deque([node_id])
        
        while queue:
            current = queue.popleft()
            for neighbor in adjacency.get(current, set()):
                if neighbor not in distances:
                    distances[neighbor] = distances[current] + 1
                    queue.append(neighbor)
        
        # Calculate closeness
        total_distance = sum(distances.values())
        reachable_nodes = len(distances) - 1  # Exclude the node itself
        
        if reachable_nodes > 0 and total_distance > 0:
            closeness = reachable_nodes / total_distance
            if normalize and len(nodes) > 1:
                closeness = closeness * reachable_nodes / (len(nodes) - 1)
            centrality[node_id] = closeness
        else:
            centrality[node_id] = 0.0
    
    return centrality

def find_communities(graph: Dict[str, Any], 
                    algorithm: str = "louvain",
                    resolution: float = 1.0) -> Dict[str, Any]:
    """
    Find communities in the graph.
    
    Args:
        graph: Graph structure
        algorithm: Community detection algorithm ("louvain", "modularity")
        resolution: Resolution parameter for community detection
        
    Returns:
        Community detection results
    """
    nodes = graph.get("nodes", {})
    edges = graph.get("edges", {})
    
    if not nodes:
        return {"communities": {}, "modularity": 0.0, "num_communities": 0}
    
    # For simplicity, implement a basic modularity-based approach
    # In practice, you might want to use networkx or igraph
    
    # Build adjacency list with weights
    adjacency = defaultdict(dict)
    total_weight = 0
    
    for edge in edges.values():
        source = edge.get("source_id") or edge.get("source")
        target = edge.get("target_id") or edge.get("target")
        weight = edge.get("weight", 1.0)
        
        if source and target:
            adjacency[source][target] = weight
            adjacency[target][source] = weight
            total_weight += weight
    
    # Simple greedy modularity optimization
    communities = _greedy_modularity_communities(nodes, adjacency, total_weight)
    
    # Calculate modularity
    modularity = _calculate_modularity(communities, adjacency, total_weight)
    
    return {
        "communities": communities,
        "modularity": modularity,
        "num_communities": len(set(communities.values())),
        "algorithm": algorithm
    }

def _greedy_modularity_communities(nodes: Dict[str, Any], 
                                  adjacency: Dict[str, Dict[str, float]], 
                                  total_weight: float) -> Dict[str, int]:
    """Simple greedy modularity-based community detection"""
    # Start with each node in its own community
    communities = {node_id: i for i, node_id in enumerate(nodes)}
    
    # Calculate node degrees
    degrees = {}
    for node_id in nodes:
        degrees[node_id] = sum(adjacency.get(node_id, {}).values())
    
    improved = True
    while improved:
        improved = False
        
        for node_id in nodes:
            current_community = communities[node_id]
            best_community = current_community
            best_gain = 0
            
            # Try moving node to neighbor communities
            neighbor_communities = set()
            for neighbor in adjacency.get(node_id, {}):
                neighbor_communities.add(communities[neighbor])
            
            for community in neighbor_communities:
                if community != current_community:
                    # Calculate modularity gain
                    gain = _modularity_gain(node_id, community, communities, 
                                          adjacency, degrees, total_weight)
                    if gain > best_gain:
                        best_gain = gain
                        best_community = community
            
            # Move node if improvement found
            if best_community != current_community:
                communities[node_id] = best_community
                improved = True
    
    return communities

def _modularity_gain(node_id: str, 
                    target_community: int,
                    communities: Dict[str, int],
                    adjacency: Dict[str, Dict[str, float]],
                    degrees: Dict[str, float],
                    total_weight: float) -> float:
    """Calculate modularity gain for moving a node to a community"""
    # Simplified modularity gain calculation
    # This is a basic implementation - real algorithms are more complex
    
    current_community = communities[node_id]
    
    # Calculate edges to target community
    edges_to_target = 0
    for neighbor, weight in adjacency.get(node_id, {}).items():
        if communities[neighbor] == target_community:
            edges_to_target += weight
    
    # Calculate edges to current community (excluding self)
    edges_to_current = 0
    for neighbor, weight in adjacency.get(node_id, {}).items():
        if communities[neighbor] == current_community and neighbor != node_id:
            edges_to_current += weight
    
    # Simplified gain calculation
    gain = (edges_to_target - edges_to_current) / total_weight
    return gain

def _calculate_modularity(communities: Dict[str, int],
                         adjacency: Dict[str, Dict[str, float]],
                         total_weight: float) -> float:
    """Calculate modularity score"""
    if total_weight == 0:
        return 0.0
    
    modularity = 0.0
    
    # Group nodes by community
    community_nodes = defaultdict(list)
    for node_id, community in communities.items():
        community_nodes[community].append(node_id)
    
    # Calculate modularity for each community
    for community, nodes in community_nodes.items():
        internal_weight = 0
        total_degree = 0
        
        for node in nodes:
            # Internal edges
            for neighbor, weight in adjacency.get(node, {}).items():
                if communities.get(neighbor) == community:
                    internal_weight += weight
            
            # Total degree
            total_degree += sum(adjacency.get(node, {}).values())
        
        # Avoid double counting internal edges
        internal_weight /= 2
        
        # Modularity contribution
        if total_weight > 0:
            modularity += (internal_weight / total_weight) - (total_degree / (2 * total_weight)) ** 2
    
    return modularity

def validate_graph_structure(graph: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate graph structure and report issues.
    
    Args:
        graph: Graph structure to validate
        
    Returns:
        Validation report
    """
    report = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "statistics": {}
    }
    
    nodes = graph.get("nodes", {})
    edges = graph.get("edges", {})
    
    # Check nodes
    if not nodes:
        report["warnings"].append("Graph has no nodes")
    
    node_ids = set(nodes.keys())
    
    # Check edges
    orphaned_edges = []
    self_loops = []
    edge_count_by_type = defaultdict(int)
    
    for edge_id, edge in edges.items():
        source = edge.get("source_id") or edge.get("source")
        target = edge.get("target_id") or edge.get("target")
        
        # Check if edge references valid nodes
        if source not in node_ids:
            orphaned_edges.append(f"Edge {edge_id} references missing source node: {source}")
        
        if target not in node_ids:
            orphaned_edges.append(f"Edge {edge_id} references missing target node: {target}")
        
        # Check for self-loops
        if source == target:
            self_loops.append(edge_id)
        
        # Count edge types
        edge_type = edge.get("relation", {}).get("type") or edge.get("edge_type", "unknown")
        edge_count_by_type[edge_type] += 1
    
    # Add errors and warnings
    if orphaned_edges:
        report["errors"].extend(orphaned_edges)
        report["valid"] = False
    
    if self_loops:
        report["warnings"].append(f"Found {len(self_loops)} self-loop edges")
    
    # Calculate statistics
    node_degrees = defaultdict(int)
    for edge in edges.values():
        source = edge.get("source_id") or edge.get("source")
        target = edge.get("target_id") or edge.get("target")
        if source in node_ids:
            node_degrees[source] += 1
        if target in node_ids:
            node_degrees[target] += 1
    
    isolated_nodes = [node_id for node_id in node_ids if node_degrees[node_id] == 0]
    
    report["statistics"] = {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "isolated_nodes": len(isolated_nodes),
        "self_loops": len(self_loops),
        "max_degree": max(node_degrees.values()) if node_degrees else 0,
        "avg_degree": sum(node_degrees.values()) / len(nodes) if nodes else 0,
        "edge_types": dict(edge_count_by_type)
    }
    
    if isolated_nodes:
        report["warnings"].append(f"Found {len(isolated_nodes)} isolated nodes")
    
    return report

def export_graph_formats(graph: Dict[str, Any], 
                         format_type: str = "gexf") -> str:
    """
    Export graph to different formats.
    
    Args:
        graph: Graph structure
        format_type: Export format ("gexf", "graphml", "dot", "json")
        
    Returns:
        Exported graph as string
    """
    if format_type == "json":
        return json.dumps(graph, indent=2)
    elif format_type == "gexf":
        return _export_gexf(graph)
    elif format_type == "graphml":
        return _export_graphml(graph)
    elif format_type == "dot":
        return _export_dot(graph)
    else:
        raise ValueError(f"Unsupported export format: {format_type}")

def _export_gexf(graph: Dict[str, Any]) -> str:
    """Export graph to GEXF format"""
    nodes = graph.get("nodes", {})
    edges = graph.get("edges", {})
    
    gexf = ['<?xml version="1.0" encoding="UTF-8"?>']
    gexf.append('<gexf xmlns="http://www.gexf.net/1.2draft" version="1.2">')
    gexf.append('  <graph mode="static" defaultedgetype="directed">')
    
    # Nodes
    gexf.append('    <nodes>')
    for node_id, node in nodes.items():
        entity = node.get("entity", {})
        label = entity.get("text", node_id)
        gexf.append(f'      <node id="{node_id}" label="{label}"/>')
    gexf.append('    </nodes>')
    
    # Edges
    gexf.append('    <edges>')
    for edge_id, edge in edges.items():
        source = edge.get("source_id") or edge.get("source")
        target = edge.get("target_id") or edge.get("target")
        weight = edge.get("weight", 1.0)
        gexf.append(f'      <edge id="{edge_id}" source="{source}" target="{target}" weight="{weight}"/>')
    gexf.append('    </edges>')
    
    gexf.append('  </graph>')
    gexf.append('</gexf>')
    
    return '\n'.join(gexf)

def _export_graphml(graph: Dict[str, Any]) -> str:
    """Export graph to GraphML format"""
    nodes = graph.get("nodes", {})
    edges = graph.get("edges", {})
    
    graphml = ['<?xml version="1.0" encoding="UTF-8"?>']
    graphml.append('<graphml xmlns="http://graphml.graphdrawing.org/xmlns">')
    graphml.append('  <graph id="G" edgedefault="directed">')
    
    # Nodes
    for node_id, node in nodes.items():
        entity = node.get("entity", {})
        label = entity.get("text", node_id)
        graphml.append(f'    <node id="{node_id}">')
        graphml.append(f'      <data key="label">{label}</data>')
        graphml.append('    </node>')
    
    # Edges
    for edge_id, edge in edges.items():
        source = edge.get("source_id") or edge.get("source")
        target = edge.get("target_id") or edge.get("target")
        weight = edge.get("weight", 1.0)
        graphml.append(f'    <edge id="{edge_id}" source="{source}" target="{target}">')
        graphml.append(f'      <data key="weight">{weight}</data>')
        graphml.append('    </edge>')
    
    graphml.append('  </graph>')
    graphml.append('</graphml>')
    
    return '\n'.join(graphml)

def _export_dot(graph: Dict[str, Any]) -> str:
    """Export graph to DOT format"""
    nodes = graph.get("nodes", {})
    edges = graph.get("edges", {})
    
    dot = ['digraph G {']
    
    # Nodes
    for node_id, node in nodes.items():
        entity = node.get("entity", {})
        label = entity.get("text", node_id)
        dot.append(f'  "{node_id}" [label="{label}"];')
    
    # Edges
    for edge in edges.values():
        source = edge.get("source_id") or edge.get("source")
        target = edge.get("target_id") or edge.get("target")
        weight = edge.get("weight", 1.0)
        dot.append(f'  "{source}" -> "{target}" [weight={weight}];')
    
    dot.append('}')
    
    return '\n'.join(dot)