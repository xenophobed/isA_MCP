#!/usr/bin/env python3
"""
Register MCP service with Consul for automatic discovery
"""

import consul
import socket
import time
import signal
import sys
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPConsulRegistration:
    def __init__(self,
                 service_name="mcp",
                 service_port=8081,
                 consul_host=None,
                 consul_port=8500,
                 service_host=None):
        """Initialize Consul registration for MCP service"""
        # Read from env vars if not provided
        consul_host = consul_host or os.getenv('CONSUL_HOST', 'localhost')
        consul_port = consul_port or int(os.getenv('CONSUL_PORT', '8500'))
        service_host = service_host or os.getenv('SERVICE_HOST', socket.gethostname())

        self.consul = consul.Consul(host=consul_host, port=consul_port)
        self.service_name = service_name
        self.service_port = service_port
        self.service_host = service_host
        self.service_id = f"{service_name}-{service_host}-{service_port}"
        self.running = True
        
    def register(self):
        """Register MCP service with Consul"""
        try:
            # Register with TTL health check (good for SSE services)
            self.consul.agent.service.register(
                name=self.service_name,
                service_id=self.service_id,
                address=self.service_host,
                port=self.service_port,
                tags=[
                    "sse",          # Server-Sent Events support
                    "mcp",          # Model Context Protocol
                    "ai",           # AI service
                    "streaming",    # Streaming responses
                    "long-polling", # Long polling support
                    "websocket",    # WebSocket support (if applicable)
                ],
                check=consul.Check.ttl("30s")  # TTL check every 30 seconds
            )
            
            # Pass initial health check
            self.consul.agent.check.ttl_pass(f"service:{self.service_id}")
            
            logger.info(f"✅ MCP service registered with Consul: {self.service_id}")
            logger.info(f"   Service: {self.service_name}")
            logger.info(f"   Port: {self.service_port}")
            logger.info(f"   Tags: sse, mcp, ai, streaming")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to register with Consul: {e}")
            return False
    
    def maintain_health(self):
        """Maintain health check with Consul"""
        while self.running:
            try:
                # Update TTL health check
                self.consul.agent.check.ttl_pass(
                    f"service:{self.service_id}",
                    "MCP service is healthy"
                )
                logger.debug("Health check passed")
                time.sleep(15)  # Update every 15 seconds
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                time.sleep(5)
    
    def deregister(self):
        """Deregister service from Consul"""
        try:
            self.consul.agent.service.deregister(self.service_id)
            logger.info(f"Service {self.service_id} deregistered from Consul")
        except Exception as e:
            logger.error(f"Failed to deregister: {e}")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("Shutdown signal received")
        self.running = False
        self.deregister()
        sys.exit(0)

def main():
    """Main function to register MCP with Consul"""
    # Create registration - will read from env vars
    service_port = int(os.getenv('SERVICE_PORT', '8081'))
    registration = MCPConsulRegistration(
        service_name="mcp",
        service_port=service_port
    )
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, registration.signal_handler)
    signal.signal(signal.SIGTERM, registration.signal_handler)
    
    # Register service
    if registration.register():
        logger.info("MCP service registered successfully")
        logger.info("Maintaining health checks... Press Ctrl+C to stop")
        
        # Maintain health checks
        registration.maintain_health()
    else:
        logger.error("Failed to register MCP service")
        sys.exit(1)

if __name__ == "__main__":
    main()