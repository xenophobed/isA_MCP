#!/usr/bin/env python
"""
Event Sourcing Demo Script
Simple demonstration of the Event-Driven MCP system
"""
import asyncio
import sys
import os

# Add paths
sys.path.append('.')
sys.path.append('client')

async def demo_web_monitoring():
    """Demo web monitoring functionality"""
    print("\n🌐 Demo: Web Content Monitoring")
    print("=" * 40)
    
    from v13_mcp_client import EventDrivenMCPClient
    
    client = EventDrivenMCPClient(use_load_balancer=True)
    
    try:
        print("📝 Creating web monitoring task...")
        response = await client.run_conversation(
            "Create a background task to monitor TechCrunch for articles about 'artificial intelligence'. "
            "Check every 30 minutes and notify me when new AI content is found."
        )
        
        print("✅ Web monitoring task created!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
    finally:
        await client.cleanup()

async def demo_news_digest():
    """Demo news digest functionality"""
    print("\n📰 Demo: Daily News Digest")
    print("=" * 40)
    
    from v13_mcp_client import EventDrivenMCPClient
    
    client = EventDrivenMCPClient(use_load_balancer=True)
    
    try:
        print("📝 Creating daily news digest task...")
        response = await client.run_conversation(
            "Set up a daily news digest that summarizes technology news from TechCrunch and Hacker News. "
            "Send me the digest every morning at 8 AM."
        )
        
        print("✅ News digest task created!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
    finally:
        await client.cleanup()

async def demo_scheduled_reminder():
    """Demo scheduled reminder functionality"""
    print("\n⏰ Demo: Scheduled Reminders")
    print("=" * 40)
    
    from v13_mcp_client import EventDrivenMCPClient
    
    client = EventDrivenMCPClient(use_load_balancer=True)
    
    try:
        print("📝 Creating scheduled reminder...")
        response = await client.run_conversation(
            "Create a daily reminder to review my project status every day at 9 AM. "
            "Send me a notification to check my tasks and progress."
        )
        
        print("✅ Scheduled reminder created!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
    finally:
        await client.cleanup()

async def demo_task_management():
    """Demo task management functionality"""
    print("\n📋 Demo: Task Management")
    print("=" * 40)
    
    from v13_mcp_client import EventDrivenMCPClient
    
    client = EventDrivenMCPClient(use_load_balancer=True)
    
    try:
        print("📝 Listing current background tasks...")
        response = await client.run_conversation(
            "Show me all my current background tasks and their status."
        )
        
        print("✅ Task list retrieved!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
    finally:
        await client.cleanup()

async def demo_event_simulation():
    """Demo event simulation"""
    print("\n🎭 Demo: Event Simulation")
    print("=" * 40)
    
    from v13_mcp_client import EventDrivenMCPClient
    
    client = EventDrivenMCPClient(use_load_balancer=True)
    
    try:
        print("📝 Simulating web content change event...")
        
        # Simulate a web content change event
        await client.simulate_event_feedback(
            task_id="demo-web-monitor",
            event_type="web_content_change",
            data={
                "url": "https://techcrunch.com",
                "content": "Breaking: New AI breakthrough announced - GPT-5 with revolutionary capabilities",
                "keywords_found": ["AI", "breakthrough", "GPT-5"],
                "description": "Monitor TechCrunch for AI news",
                "user_id": "demo_user"
            }
        )
        
        print("✅ Event simulation completed!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
    finally:
        await client.cleanup()

async def main():
    """Main demo function"""
    print("🎯 Event Sourcing MCP System Demo")
    print("=" * 50)
    print("This demo showcases the Event-Driven capabilities:")
    print("  • Web content monitoring")
    print("  • Daily news digests")
    print("  • Scheduled reminders")
    print("  • Task management")
    print("  • Event simulation")
    
    # Check if servers are running
    print("\n🔍 Checking system status...")
    
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            # Check Event Feedback Server
            async with session.get('http://localhost:8000/health') as response:
                if response.status == 200:
                    print("✅ Event Feedback Server is running")
                else:
                    print("⚠️ Event Feedback Server may not be running")
            
            # Check MCP Load Balancer
            try:
                async with session.get('http://localhost/health') as response:
                    print("✅ MCP Load Balancer is accessible")
            except:
                print("⚠️ MCP Load Balancer may not be running")
                
    except Exception as e:
        print(f"⚠️ System check failed: {e}")
    
    print("\n🎮 Starting demos...")
    
    demos = [
        ("Web Monitoring", demo_web_monitoring),
        ("News Digest", demo_news_digest),
        ("Scheduled Reminder", demo_scheduled_reminder),
        ("Task Management", demo_task_management),
        ("Event Simulation", demo_event_simulation)
    ]
    
    for demo_name, demo_func in demos:
        try:
            print(f"\n🚀 Running {demo_name} demo...")
            await demo_func()
            print(f"✅ {demo_name} demo completed")
        except Exception as e:
            print(f"❌ {demo_name} demo failed: {e}")
        
        # Wait between demos
        await asyncio.sleep(1)
    
    print("\n🎉 All demos completed!")
    print("\n📊 To monitor events in real-time, visit:")
    print("  • Event Dashboard: http://localhost:8000/events")
    print("  • Health Check: http://localhost:8000/health")
    print("  • MCP Load Balancer: http://localhost/")

if __name__ == "__main__":
    print("🎯 Event Sourcing Demo")
    print("Make sure the following are running:")
    print("  1. Event Feedback Server (python event_feedback_server.py)")
    print("  2. MCP Servers (docker-compose up -d)")
    print("  3. Load Balancer (nginx)")
    
    choice = input("\n🤔 Ready to run demos? (y/n): ").strip().lower()
    
    if choice == 'y':
        asyncio.run(main())
    else:
        print("👋 Demo cancelled. Run the servers first, then try again.") 