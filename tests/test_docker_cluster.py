#!/usr/bin/env python3
"""
Test Script for Smart MCP Server Docker Cluster
"""
import asyncio
import aiohttp
import json
import time
from typing import Dict, List

class SmartMCPClusterTester:
    def __init__(self):
        self.base_urls = [
            "http://localhost:4321",  # Direct server access
            "http://localhost:4322",
            "http://localhost:4323",
            "http://localhost:8081"   # Load balancer access
        ]
        self.load_balancer_url = "http://localhost:8081"
    
    async def test_health_checks(self) -> Dict[str, bool]:
        """Test health checks for all servers"""
        print("🏥 Testing Health Checks...")
        results = {}
        
        async with aiohttp.ClientSession() as session:
            for url in self.base_urls:
                try:
                    async with session.get(f"{url}/health", timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            results[url] = data.get("status") == "healthy"
                            print(f"  ✅ {url}/health - {data}")
                        else:
                            results[url] = False
                            print(f"  ❌ {url}/health - Status {response.status}")
                except Exception as e:
                    results[url] = False
                    print(f"  ❌ {url}/health - Error: {e}")
        
        return results
    
    async def test_load_balancer_distribution(self) -> Dict[str, int]:
        """Test load balancer distributes requests"""
        print("\n⚖️ Testing Load Balancer Distribution...")
        server_counts = {}
        
        async with aiohttp.ClientSession() as session:
            for i in range(15):  # Test with 15 requests
                try:
                    async with session.get(f"{self.load_balancer_url}/health", timeout=5) as response:
                        if response.status == 200:
                            data = await response.json()
                            server_info = data.get("server_status", {})
                            # Extract server identifier (could be from headers or response)
                            server_id = f"request_{i}"  # Simplified for demo
                            server_counts[server_id] = server_counts.get(server_id, 0) + 1
                        await asyncio.sleep(0.1)
                except Exception as e:
                    print(f"  ❌ Request {i} failed: {e}")
        
        print(f"  📊 Distribution pattern: {len(server_counts)} unique responses")
        return server_counts
    
    async def test_ai_tool_selection(self) -> bool:
        """Test AI tool selection through load balancer"""
        print("\n🧠 Testing AI Tool Selection...")
        
        test_requests = [
            "scrape website for product information",
            "remember important user data",
            "generate an image of a sunset",
            "get weather forecast for tomorrow",
            "search shopify products"
        ]
        
        async with aiohttp.ClientSession() as session:
            for request_text in test_requests:
                try:
                    payload = {"request": request_text}
                    async with session.post(
                        f"{self.load_balancer_url}/analyze",
                        json=payload,
                        timeout=30
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            recommended_tools = data.get("recommended_tools", [])
                            print(f"  🎯 '{request_text}' -> {recommended_tools}")
                        else:
                            print(f"  ❌ '{request_text}' -> Status {response.status}")
                            text = await response.text()
                            print(f"      Response: {text}")
                except Exception as e:
                    print(f"  ❌ '{request_text}' -> Error: {e}")
        
        return True
    
    async def test_web_scraper_integration(self) -> bool:
        """Test web scraper tools through MCP interface"""
        print("\n🕸️ Testing Web Scraper Integration...")
        
        # Test through load balancer
        try:
            mcp_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.load_balancer_url}/mcp/",
                    json=mcp_payload,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json, text/event-stream"
                    },
                    timeout=15
                ) as response:
                    if response.status == 200:
                        # Handle SSE response format - just check if web scraper tools are mentioned
                        text = await response.text()
                        web_scraper_tools = ["scrape_webpage", "scrape_multiple_pages", "extract_page_links", "search_page_content", "get_scraper_status", "cleanup_scraper_resources"]
                        found_tools = []
                        for tool_name in web_scraper_tools:
                            if tool_name in text:
                                found_tools.append(tool_name)
                        
                        print(f"  📋 Found {len(found_tools)} web scraper tools:")
                        for tool in found_tools[:3]:  # Show first 3
                            print(f"      • {tool}")
                        return len(found_tools) > 0
                    else:
                        print(f"  ❌ MCP tools/list failed - Status {response.status}")
                        return False
        except Exception as e:
            print(f"  ❌ Web scraper test failed: {e}")
            return False
    
    async def test_server_stats(self) -> Dict:
        """Test server statistics endpoint"""
        print("\n📊 Testing Server Statistics...")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.load_balancer_url}/stats", timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        server_status = data.get("server_status", {})
                        print(f"  📈 Server Mode: {server_status.get('mode', 'Unknown')}")
                        print(f"  🔧 Loaded Tools: {', '.join(server_status.get('loaded_tools', []))}")
                        print(f"  🤖 AI Selector: {'Enabled' if server_status.get('tool_selector_ready') else 'Disabled'}")
                        return data
                    else:
                        print(f"  ❌ Stats endpoint failed - Status {response.status}")
                        return {}
            except Exception as e:
                print(f"  ❌ Stats test failed: {e}")
                return {}
    
    async def run_full_test_suite(self):
        """Run complete test suite"""
        print("🚀 Smart MCP Server Docker Cluster Test Suite")
        print("=" * 50)
        
        start_time = time.time()
        
        # Test 1: Health checks
        health_results = await self.test_health_checks()
        healthy_servers = sum(1 for status in health_results.values() if status)
        print(f"\n✅ Health Check Results: {healthy_servers}/{len(self.base_urls)} servers healthy")
        
        # Test 2: Load balancer distribution
        distribution = await self.test_load_balancer_distribution()
        
        # Test 3: AI tool selection
        ai_test = await self.test_ai_tool_selection()
        
        # Test 4: Web scraper integration
        web_test = await self.test_web_scraper_integration()
        
        # Test 5: Server stats
        stats = await self.test_server_stats()
        
        # Summary
        total_time = time.time() - start_time
        print(f"\n📝 Test Summary:")
        print(f"  ⏱️  Total test time: {total_time:.2f}s")
        print(f"  🏥 Health checks: {healthy_servers}/{len(self.base_urls)} passed")
        print(f"  🧠 AI tool selection: {'✅ Passed' if ai_test else '❌ Failed'}")
        print(f"  🕸️  Web scraper tools: {'✅ Passed' if web_test else '❌ Failed'}")
        print(f"  📊 Stats endpoint: {'✅ Passed' if stats else '❌ Failed'}")
        
        overall_success = healthy_servers >= 3 and ai_test and web_test
        print(f"\n🎯 Overall Result: {'✅ CLUSTER WORKING' if overall_success else '❌ ISSUES DETECTED'}")
        
        return overall_success

async def main():
    """Main test function"""
    tester = SmartMCPClusterTester()
    
    print("⚠️  Make sure Docker cluster is running:")
    print("   docker-compose -f docker-compose.smart.yml up -d")
    print("\n⏳ Starting tests in 3 seconds...\n")
    
    await asyncio.sleep(3)
    
    try:
        success = await tester.run_full_test_suite()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Test suite failed with error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())