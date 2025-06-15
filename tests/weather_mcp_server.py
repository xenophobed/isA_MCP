import asyncio
import json
import sys
import os
import logging
import random
from typing import List, Dict, Any

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 使用 FastMCP
from fastmcp import FastMCP, Transport

# 设置日志
logging.basicConfig(level=logging.INFO, 
                  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("weather-mcp-server")

# 创建 MCP 服务器
mcp = FastMCP("Weather-Service")

# 全局天气数据 (模拟数据)
WEATHER_DATA = {
    "london": {
        "temperature": 15,
        "conditions": "Cloudy",
        "humidity": 75,
        "wind_speed": 10
    },
    "tokyo": {
        "temperature": 25,
        "conditions": "Sunny",
        "humidity": 60,
        "wind_speed": 5
    },
    "new york": {
        "temperature": 20,
        "conditions": "Partly Cloudy",
        "humidity": 65,
        "wind_speed": 8
    },
    "sydney": {
        "temperature": 22,
        "conditions": "Sunny",
        "humidity": 50,
        "wind_speed": 12
    },
    "paris": {
        "temperature": 18,
        "conditions": "Rainy",
        "humidity": 80,
        "wind_speed": 15
    },
    "beijing": {
        "temperature": 28,
        "conditions": "Sunny",
        "humidity": 45,
        "wind_speed": 6
    },
    "cairo": {
        "temperature": 32,
        "conditions": "Hot",
        "humidity": 30,
        "wind_speed": 7
    },
    "moscow": {
        "temperature": 5,
        "conditions": "Snowy",
        "humidity": 85,
        "wind_speed": 20
    },
    "rio de janeiro": {
        "temperature": 30,
        "conditions": "Sunny",
        "humidity": 70,
        "wind_speed": 8
    },
    "toronto": {
        "temperature": 8,
        "conditions": "Cloudy",
        "humidity": 60,
        "wind_speed": 15
    }
}

@mcp.tool
async def get_weather(city: str) -> Dict[str, Any]:
    """
    获取指定城市的天气信息
    
    Args:
        city: 城市名称(如 London, Tokyo, New York)
        
    Returns:
        Dict[str, Any]: 包含温度、天气状况、湿度和风速的天气信息
    """
    city_lower = city.lower()
    
    # 添加随机延迟以模拟网络请求
    await asyncio.sleep(random.uniform(0.5, 1.5))
    
    if city_lower in WEATHER_DATA:
        logger.info(f"获取 {city} 的天气信息")
        return {
            "city": city,
            "temperature": WEATHER_DATA[city_lower]["temperature"],
            "conditions": WEATHER_DATA[city_lower]["conditions"],
            "humidity": WEATHER_DATA[city_lower]["humidity"],
            "wind_speed": WEATHER_DATA[city_lower]["wind_speed"],
            "unit": "celsius"
        }
    else:
        logger.warning(f"未找到 {city} 的天气信息")
        return {
            "city": city,
            "error": "城市未找到",
            "available_cities": list(WEATHER_DATA.keys())
        }

@mcp.tool
async def find_cool_cities(max_temperature: int = 20) -> List[Dict[str, Any]]:
    """
    查找温度低于指定值的凉爽城市
    
    Args:
        max_temperature: 最高温度(摄氏度)，默认为20度
        
    Returns:
        List[Dict[str, Any]]: 满足条件的城市及其天气信息列表
    """
    # 添加随机延迟以模拟网络请求
    await asyncio.sleep(random.uniform(0.8, 2.0))
    
    cool_cities = []
    
    for city, data in WEATHER_DATA.items():
        if data["temperature"] <= max_temperature:
            cool_cities.append({
                "city": city.title(),
                "temperature": data["temperature"],
                "conditions": data["conditions"]
            })
    
    logger.info(f"找到 {len(cool_cities)} 个温度低于 {max_temperature}°C 的城市")
    return cool_cities

@mcp.tool
async def get_weather_comparison(cities: List[str]) -> Dict[str, Any]:
    """
    比较多个城市的天气情况
    
    Args:
        cities: 城市名称列表
        
    Returns:
        Dict[str, Any]: 城市天气比较结果
    """
    # 添加随机延迟以模拟网络请求
    await asyncio.sleep(random.uniform(1.0, 2.5))
    
    results = {}
    not_found = []
    
    for city in cities:
        city_lower = city.lower()
        if city_lower in WEATHER_DATA:
            results[city] = WEATHER_DATA[city_lower]
        else:
            not_found.append(city)
    
    if not_found:
        logger.warning(f"未找到以下城市的天气信息: {', '.join(not_found)}")
    
    # 找出最热和最冷的城市
    if results:
        temps = [(city, data["temperature"]) for city, data in results.items()]
        hottest = max(temps, key=lambda x: x[1])
        coldest = min(temps, key=lambda x: x[1])
        
        return {
            "cities": results,
            "not_found": not_found,
            "hottest_city": hottest[0],
            "hottest_temperature": hottest[1],
            "coldest_city": coldest[0],
            "coldest_temperature": coldest[1],
            "unit": "celsius"
        }
    else:
        return {
            "error": "未找到任何指定城市的天气信息",
            "not_found": not_found,
            "available_cities": list(WEATHER_DATA.keys())
        }

# 主函数
async def main():
    logger.info("启动天气 MCP 服务器...")
    
    # 在开发模式下运行服务器
    await mcp.run(
        transport=Transport.STREAMABLE_HTTP,
        host="127.0.0.1",
        port=8000,
        path="/mcp"
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("服务器已停止")
    except Exception as e:
        logger.error(f"服务器发生错误: {str(e)}")
        import traceback
        logger.error(traceback.format_exc()) 