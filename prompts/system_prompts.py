#!/usr/bin/env python
"""
System Prompts for MCP Server
Provides dynamic prompt templates for various operations
"""
from datetime import datetime

from core.logging import get_logger

logger = get_logger(__name__)

def register_system_prompts(mcp):
    """Register all system prompts with the MCP server"""
    
    @mcp.prompt()
    async def security_analysis_prompt(context: str = "", operation: str = "") -> str:
        """Generate a security analysis prompt for evaluating operations"""
        
        return f"""You are a security analyst evaluating the following operation for potential risks:

Operation: {operation}
Context: {context}

Please analyze this operation and provide:
1. Security risk level (LOW/MEDIUM/HIGH/CRITICAL)
2. Potential security concerns
3. Recommended mitigation strategies
4. Authorization requirements

Consider:
- Data sensitivity
- System impact
- User permissions
- Audit requirements
- Compliance implications

Provide your analysis in structured JSON format."""
    
    @mcp.prompt()
    async def memory_organization_prompt(memories: str = "", query: str = "") -> str:
        """Generate a prompt for organizing and categorizing memories"""
        
        return f"""You are a knowledge organization specialist. Help organize and categorize the following memories:

Query: {query}
Memories to organize: {memories}

Please provide:
1. Suggested categories for better organization
2. Importance ratings (1-5 scale)
3. Relationships between memories
4. Recommendations for memory consolidation
5. Search optimization suggestions

Format your response as structured JSON with clear recommendations."""
    
    @mcp.prompt()
    async def monitoring_report_prompt(metrics: str = "", timeframe: str = "recent") -> str:
        """Generate a monitoring and performance analysis prompt"""
        
        return f"""You are a system monitoring specialist. Analyze the following system metrics:

Timeframe: {timeframe}
Metrics Data: {metrics}

Please provide:
1. System health assessment
2. Performance trend analysis
3. Anomaly detection
4. Resource utilization insights
5. Recommendations for optimization
6. Alert thresholds suggestions

Focus on:
- Request patterns
- Error rates
- Security events
- Resource consumption
- User activity patterns

Format as a comprehensive monitoring report in JSON structure."""
    
    @mcp.prompt()
    async def user_assistance_prompt(user_query: str = "", context: str = "") -> str:
        """Generate a user assistance prompt for helping with queries"""
        
        return f"""You are a helpful AI assistant with access to memory, weather, and administrative tools.

User Query: {user_query}
Context: {context}
Current Time: {datetime.now().isoformat()}

Guidelines:
1. Be helpful and accurate
2. Ask for clarification when needed
3. Respect security and privacy policies
4. Use appropriate tools to fulfill requests
5. Provide structured, clear responses
6. Follow authorization requirements for sensitive operations

Available capabilities:
- Memory operations (remember, search, forget)
- Weather information
- System monitoring
- Administrative functions

Respond in a helpful, professional manner while maintaining security best practices."""

    logger.info("System prompts registered successfully") 