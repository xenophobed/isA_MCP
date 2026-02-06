#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standard Process Resources - MCP Resource Registration

Provides standard workflows and best practice processes for common tasks.
Agents can reference these processes when creating execution plans.

Features:
- Pre-defined standard workflows for common scenarios
- Best practice templates for different domains
- Process discovery and matching
- Quality assurance checklists
"""

import json
import logging
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


# ============================================================================
# STANDARD PROCESS DEFINITIONS
# ============================================================================

STANDARD_PROCESSES = {
    "code_security_audit": {
        "process_id": "code_security_audit",
        "name": "Code Security Audit",
        "description": "Comprehensive code security audit workflow",
        "domain": "security",
        "complexity": "high",
        "estimated_tasks": 4,
        "steps": [
            {
                "step": 1,
                "action": "Dependency Analysis",
                "description": "Analyze project dependencies and third-party libraries",
                "required_tools": ["code_search", "web_search"],
                "verification": "All dependencies documented with versions",
                "output": "Dependency list"
            },
            {
                "step": 2,
                "action": "Vulnerability Scanning",
                "description": "Scan for known vulnerabilities and CVEs",
                "required_tools": ["web_search", "data_query"],
                "verification": "All CVEs documented with severity ratings",
                "output": "Vulnerability report"
            },
            {
                "step": 3,
                "action": "Code Review",
                "description": "Review code for security issues and best practices",
                "required_tools": ["code_search"],
                "verification": "All code patterns analyzed",
                "output": "Code review findings"
            },
            {
                "step": 4,
                "action": "Report Generation",
                "description": "Generate comprehensive security audit report",
                "required_tools": ["ask_human"],
                "verification": "Report includes all findings and recommendations",
                "output": "Complete security report"
            }
        ],
        "success_criteria": [
            "All dependencies audited",
            "Vulnerabilities categorized by severity",
            "Recommendations provided"
        ],
        "keywords": ["security", "audit", "code", "vulnerability", "scanning"]
    },

    "data_analysis_workflow": {
        "process_id": "data_analysis_workflow",
        "name": "Data Analysis Workflow",
        "description": "Complete data analysis workflow from ingestion to insights",
        "domain": "data_science",
        "complexity": "medium",
        "estimated_tasks": 5,
        "steps": [
            {
                "step": 1,
                "action": "Data Collection",
                "description": "Collect and ingest data from various sources",
                "required_tools": ["data_ingest", "web_crawl"],
                "verification": "Data successfully ingested and validated",
                "output": "Raw dataset"
            },
            {
                "step": 2,
                "action": "Data Cleaning",
                "description": "Clean and preprocess data",
                "required_tools": ["data_query"],
                "verification": "Data quality metrics meet thresholds",
                "output": "Clean dataset"
            },
            {
                "step": 3,
                "action": "Exploratory Analysis",
                "description": "Perform exploratory data analysis",
                "required_tools": ["data_query", "data_search"],
                "verification": "Key patterns and distributions identified",
                "output": "EDA report"
            },
            {
                "step": 4,
                "action": "Statistical Analysis",
                "description": "Apply statistical methods and modeling",
                "required_tools": ["data_query"],
                "verification": "Models validated with metrics",
                "output": "Analysis results"
            },
            {
                "step": 5,
                "action": "Results Presentation",
                "description": "Generate visualizations and report",
                "required_tools": ["ask_human"],
                "verification": "Results clearly communicated",
                "output": "Data insights report"
            }
        ],
        "success_criteria": [
            "Data quality validated",
            "Insights actionable",
            "Recommendations clear"
        ],
        "keywords": ["data", "analysis", "statistics", "insights", "visualization"]
    },

    "web_research_process": {
        "process_id": "web_research_process",
        "name": "Web Research Process",
        "description": "Systematic web research and information gathering",
        "domain": "research",
        "complexity": "low",
        "estimated_tasks": 3,
        "steps": [
            {
                "step": 1,
                "action": "Initial Search",
                "description": "Conduct initial web searches for information",
                "required_tools": ["web_search"],
                "verification": "Relevant sources identified",
                "output": "Information sources"
            },
            {
                "step": 2,
                "action": "Content Extraction",
                "description": "Extract detailed content from sources",
                "required_tools": ["web_crawl"],
                "verification": "Content extracted and validated",
                "output": "Extracted data"
            },
            {
                "step": 3,
                "action": "Information Synthesis",
                "description": "Synthesize findings into coherent summary",
                "required_tools": ["search_knowledge", "knowledge_response"],
                "verification": "Information organized and verified",
                "output": "Research summary"
            }
        ],
        "success_criteria": [
            "Information comprehensive",
            "Sources credible",
            "Summary clear"
        ],
        "keywords": ["research", "web", "search", "information", "gathering"]
    },

    "api_integration_setup": {
        "process_id": "api_integration_setup",
        "name": "API Integration Setup",
        "description": "Setup and test API integration workflow",
        "domain": "development",
        "complexity": "medium",
        "estimated_tasks": 4,
        "steps": [
            {
                "step": 1,
                "action": "API Documentation Review",
                "description": "Review API documentation and requirements",
                "required_tools": ["web_search", "web_crawl"],
                "verification": "API endpoints and authentication understood",
                "output": "API specification"
            },
            {
                "step": 2,
                "action": "Authentication Setup",
                "description": "Configure API credentials and authentication",
                "required_tools": ["ask_human"],
                "verification": "Authentication successful",
                "output": "Auth configuration"
            },
            {
                "step": 3,
                "action": "Integration Testing",
                "description": "Test API calls and responses",
                "required_tools": ["web_automation"],
                "verification": "All endpoints tested successfully",
                "output": "Test results"
            },
            {
                "step": 4,
                "action": "Error Handling",
                "description": "Implement error handling and monitoring",
                "required_tools": ["ask_human"],
                "verification": "Error cases handled properly",
                "output": "Production-ready integration"
            }
        ],
        "success_criteria": [
            "API calls successful",
            "Authentication working",
            "Error handling complete"
        ],
        "keywords": ["api", "integration", "development", "testing", "monitoring"]
    },

    "content_creation_workflow": {
        "process_id": "content_creation_workflow",
        "name": "Content Creation Workflow",
        "description": "High-quality content creation workflow",
        "domain": "content",
        "complexity": "medium",
        "estimated_tasks": 4,
        "steps": [
            {
                "step": 1,
                "action": "Research",
                "description": "Research topic and gather information",
                "required_tools": ["web_search", "search_knowledge"],
                "verification": "Sufficient information gathered",
                "output": "Research notes"
            },
            {
                "step": 2,
                "action": "Outline Creation",
                "description": "Create content structure and outline",
                "required_tools": ["ask_human"],
                "verification": "Outline approved by stakeholders",
                "output": "Content outline"
            },
            {
                "step": 3,
                "action": "Content Writing",
                "description": "Write the main content",
                "required_tools": ["knowledge_response"],
                "verification": "Content meets quality standards",
                "output": "Draft content"
            },
            {
                "step": 4,
                "action": "Review and Edit",
                "description": "Review and refine content",
                "required_tools": ["ask_human"],
                "verification": "Final content approved",
                "output": "Published content"
            }
        ],
        "success_criteria": [
            "Content accurate",
            "Quality high",
            "Stakeholders satisfied"
        ],
        "keywords": ["content", "writing", "creation", "editing", "quality"]
    }
}


# ============================================================================
# PROCESS MATCHING AND DISCOVERY
# ============================================================================

class ProcessMatcher:
    """Match user requests to standard processes"""

    @staticmethod
    def find_matching_processes(
        user_request: str,
        user_context: Optional[Dict[str, Any]] = None,
        max_results: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Find standard processes that match the user request

        Args:
            user_request: User's task request
            user_context: Additional context (domain, complexity preference, etc.)
            max_results: Maximum number of matches to return

        Returns:
            List of matching processes with relevance scores
        """
        request_lower = user_request.lower()
        matches = []

        for process_id, process in STANDARD_PROCESSES.items():
            score = 0.0

            # Check keywords match
            keywords_matched = sum(
                1 for kw in process["keywords"]
                if kw in request_lower
            )
            score += keywords_matched * 0.3

            # Check domain match if specified
            if user_context and "domain" in user_context:
                if user_context["domain"] == process["domain"]:
                    score += 0.4

            # Check name and description match
            if any(word in request_lower for word in process["name"].lower().split()):
                score += 0.2

            if score > 0:
                matches.append({
                    **process,
                    "relevance_score": round(score, 2)
                })

        # Sort by relevance score
        matches.sort(key=lambda x: x["relevance_score"], reverse=True)
        return matches[:max_results]

    @staticmethod
    def get_process_by_id(process_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific process by ID"""
        return STANDARD_PROCESSES.get(process_id)

    @staticmethod
    def list_all_processes(domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all available processes, optionally filtered by domain"""
        if domain:
            return [
                p for p in STANDARD_PROCESSES.values()
                if p["domain"] == domain
            ]
        return list(STANDARD_PROCESSES.values())


# ============================================================================
# MCP RESOURCE REGISTRATION
# ============================================================================

def register_process_resource(mcp: FastMCP):
    """
    Register standard process resources with MCP server

    IMPORTANT: Standard processes reference tools that are actually registered
    in the MCP server. This ensures reliability - processes are based on real
    capabilities, not runtime queries that might miss tools.
    """

    # Validate that processes use real MCP tools
    async def validate_process_tools():
        """Validate that all tools referenced in processes exist in MCP"""
        all_tools = await mcp.list_tools()
        mcp_tool_names = {tool.name for tool in all_tools}

        validation_results = []
        for process_id, process in STANDARD_PROCESSES.items():
            missing_tools = []
            for step in process["steps"]:
                for tool_name in step["required_tools"]:
                    if tool_name not in mcp_tool_names:
                        missing_tools.append(tool_name)

            if missing_tools:
                validation_results.append({
                    "process": process_id,
                    "missing_tools": missing_tools,
                    "status": "warning"
                })
            else:
                validation_results.append({
                    "process": process_id,
                    "status": "valid"
                })

        logger.debug(f"Process validation: {len([r for r in validation_results if r['status'] == 'valid'])}/{len(STANDARD_PROCESSES)} valid")
        if any(r['status'] == 'warning' for r in validation_results):
            for result in validation_results:
                if result['status'] == 'warning':
                    logger.debug(f"Process '{result['process']}' references missing tools: {result['missing_tools']}")

        return validation_results

    # Run validation (async, don't block registration)
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(validate_process_tools())
        else:
            asyncio.run(validate_process_tools())
    except:
        pass  # Validation is optional

    @mcp.resource("process://catalog/all")
    def get_all_processes() -> str:
        """
        Get catalog of all available standard processes

        This resource provides the complete catalog of standard workflows
        and best practice processes that agents can reference when planning.

        Keywords: process, workflow, standard, catalog, planning, best-practice
        Category: planning
        """
        processes_list = list(STANDARD_PROCESSES.values())
        return json.dumps({
            "description": "Standard Process Catalog",
            "total_processes": len(processes_list),
            "processes": [
                {
                    "id": p["process_id"],
                    "name": p["name"],
                    "domain": p["domain"],
                    "complexity": p["complexity"],
                    "estimated_tasks": p["estimated_tasks"],
                    "keywords": p["keywords"]
                }
                for p in processes_list
            ],
            "usage": "Reference these processes when creating execution plans for common tasks"
        }, indent=2, ensure_ascii=False)

    @mcp.resource("process://detail/{process_id}")
    def get_process_detail(process_id: str) -> str:
        """
        Get detailed steps and requirements for a specific process

        This resource provides complete details of a standard process including
        all steps, required tools, verification criteria, and success metrics.

        Keywords: process, detail, steps, workflow, requirements, implementation
        Category: planning
        """
        matcher = ProcessMatcher()
        process = matcher.get_process_by_id(process_id)

        if not process:
            return json.dumps({
                "error": f"Process '{process_id}' not found",
                "available_processes": list(STANDARD_PROCESSES.keys())
            }, indent=2, ensure_ascii=False)

        return json.dumps({
            "description": f"Detailed process: {process['name']}",
            "process": process,
            "usage": "Follow these steps when executing this type of task"
        }, indent=2, ensure_ascii=False)

    @mcp.resource("process://search")
    def search_processes() -> str:
        """
        Search for processes matching a query or domain

        This resource helps find the most relevant standard process
        for a given task or domain.

        Keywords: process, search, match, find, discovery, relevant
        Category: planning
        """
        return json.dumps({
            "description": "Process Search Guide",
            "search_methods": {
                "by_keywords": "Search using task-related keywords (security, data, research, etc.)",
                "by_domain": "Filter by domain (security, data_science, research, development, content)",
                "by_complexity": "Filter by complexity level (low, medium, high)"
            },
            "example_usage": "Use ProcessMatcher.find_matching_processes(user_request)",
            "available_domains": list(set(p["domain"] for p in STANDARD_PROCESSES.values()))
        }, indent=2, ensure_ascii=False)

    logger.debug(f"Registered {len(STANDARD_PROCESSES)} standard process resources")


# Export for use in planning tools
__all__ = [
    'STANDARD_PROCESSES',
    'ProcessMatcher',
    'register_process_resource'
]
