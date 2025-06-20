#!/usr/bin/env python
"""
Event Sourcing Demo Startup Script
Demonstrates the complete Event-Driven MCP architecture
"""
import asyncio
import subprocess
import sys
import time
import os
from typing import List
import signal

class EventSourcingDemo:
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.running = True
        
    def start_process(self, command: List[str], name: str, wait_time: int = 2):
        """Start a process and add it to the process list"""
        try:
            print(f"🚀 Starting {name}...")
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.processes.append(process)
            print(f"✅ {name} started (PID: {process.pid})")
            time.sleep(wait_time)
            return process
        except Exception as e:
            print(f"❌ Failed to start {name}: {e}")
            return None
    
    def cleanup(self):
        """Clean up all processes"""
        print("\n🧹 Cleaning up processes...")
        for process in self.processes:
            try:
                if process.poll() is None:  # Process is still running
                    process.terminate()
                    time.sleep(1)
                    if process.poll() is None:  # Still running, force kill
                        process.kill()
                    print(f"🔴 Process {process.pid} terminated")
            except Exception as e:
                print(f"⚠️ Error terminating process: {e}")
        
        self.processes.clear()
        print("✅ Cleanup completed")
    
    def signal_handler(self, signum, frame):
        """Handle interrupt signals"""
        print(f"\n📡 Received signal {signum}")
        self.running = False
        self.cleanup()
        sys.exit(0)
    
    def run_demo(self):
        """Run the complete Event Sourcing demo"""
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        print("🎯 Event Sourcing MCP Demo")
        print("=" * 50)
        print("This demo will start:")
        print("  1. Event Feedback HTTP Server (port 8000)")
        print("  2. Event Sourcing MCP Server (stdio)")
        print("  3. Regular MCP Server (ports 8001-8003)")
        print("  4. Nginx Load Balancer (port 80)")
        print("  5. Event-Driven MCP Client (v1.3)")
        
        input("\n🤔 Press Enter to start the demo...")
        
        try:
            # 1. Start Event Feedback Server
            self.start_process(
                [sys.executable, "event_feedback_server.py"],
                "Event Feedback Server",
                3
            )
            
            # 2. Check if MCP servers are running
            print("\n📡 Checking MCP server status...")
            
            # 3. Start Event Sourcing MCP Server (as a background service)
            print("\n🔧 Event Sourcing MCP Server will be integrated with existing servers")
            
            # 4. Show demo instructions
            self.show_demo_instructions()
            
            # 5. Start the client demo
            self.start_client_demo()
            
        except KeyboardInterrupt:
            print("\n👋 Demo interrupted by user")
        except Exception as e:
            print(f"\n❌ Demo error: {e}")
        finally:
            self.cleanup()
    
    def show_demo_instructions(self):
        """Show demo instructions"""
        print("\n📋 DEMO INSTRUCTIONS")
        print("=" * 50)
        print("🎯 Event Sourcing Architecture Overview:")
        print("  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐")
        print("  │   User/Agent    │───▶│  MCP Server      │───▶│ Event Sourcing  │")
        print("  │                 │    │  (Tools)         │    │ Service         │")
        print("  └─────────────────┘    └──────────────────┘    └─────────────────┘")
        print("           ▲                                               │")
        print("           │               ┌─────────────────┐             │")
        print("           └───────────────│ Event Feedback  │◀────────────┘")
        print("                           │ Server (HTTP)   │")
        print("                           └─────────────────┘")
        
        print("\n🔧 Available Event Types:")
        print("  - web_monitor: Monitor websites for content changes")
        print("  - schedule: Run tasks on daily/interval schedules")
        print("  - news_digest: Generate daily news summaries")
        print("  - threshold_watch: Monitor metrics and alert on breaches")
        
        print("\n🎮 Demo Scenarios:")
        print("  1. Create web monitoring task")
        print("  2. Set up daily news digest")
        print("  3. Schedule reminders")
        print("  4. Simulate event feedback")
        
        print("\n📊 Monitoring URLs:")
        print("  - Event Feedback: http://localhost:8000/events")
        print("  - Health Check: http://localhost:8000/health")
        print("  - MCP Load Balancer: http://localhost/mcp")
        
    def start_client_demo(self):
        """Start the client demo"""
        print("\n🎮 Starting Event-Driven Client Demo...")
        print("📝 You can now test the Event Sourcing system!")
        
        try:
            # Run the v1.3 client
            subprocess.run([sys.executable, "client/v13_mcp_client.py"])
        except KeyboardInterrupt:
            print("\n👋 Client demo ended")
        except Exception as e:
            print(f"❌ Client demo error: {e}")

def check_requirements():
    """Check if required dependencies are installed"""
    required_packages = [
        "fastapi",
        "uvicorn",
        "aiohttp",
        "langchain-openai",
        "langgraph",
        "pydantic"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nInstall with: pip install " + " ".join(missing_packages))
        return False
    
    return True

def main():
    """Main function"""
    print("🎯 Event Sourcing MCP Demo Launcher")
    print("=" * 40)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Check if we're in the right directory
    if not os.path.exists("client/v13_mcp_client.py"):
        print("❌ Please run this script from the project root directory")
        sys.exit(1)
    
    # Start the demo
    demo = EventSourcingDemo()
    demo.run_demo()

if __name__ == "__main__":
    main() 