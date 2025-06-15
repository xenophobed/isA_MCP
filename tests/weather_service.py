import asyncio
import logging
import sys
import os
import random

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mcp.server.fastmcp import FastMCP

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("weather-service")

# 创建MCP服务器
mcp = FastMCP("Weather Service")

# 注册原生MCP工具
@mcp.tool(name="get_weather")
async def get_weather_mcp(location: str) -> str:
    """获取指定位置的天气信息"""
    logger.info(f"获取天气: {location}")
    
    # 直接实现天气功能，而不是调用LangChain工具
    import random
    weather_conditions = ["Sunny", "Partly cloudy", "Cloudy", "Rainy", "Stormy", "Snowy", "Foggy", "Windy"]
    
    # 生成随机天气数据
    temp_c = random.randint(-10, 35)
    temp_f = (temp_c * 9/5) + 32
    condition = random.choice(weather_conditions)
    humidity = random.randint(30, 95)
    wind_speed = random.randint(0, 30)
    
    return f"{location}的天气: {condition}, 温度{temp_c}°C ({temp_f:.1f}°F), 湿度{humidity}%, 风速{wind_speed}km/h"

@mcp.tool(name="get_coolest_cities")
async def get_coolest_cities_mcp() -> str:
    """获取当前温度最低的城市列表"""
    logger.info("获取最凉爽城市列表")
    
    # 直接实现最凉爽城市功能，不依赖LangChain工具
    import random
    
    # 模拟数据
    cities = [
        {"name": "Reykjavik", "country": "Iceland", "celsius": random.randint(-5, 10)},
        {"name": "Oslo", "country": "Norway", "celsius": random.randint(-2, 15)},
        {"name": "Stockholm", "country": "Sweden", "celsius": random.randint(0, 15)},
        {"name": "Helsinki", "country": "Finland", "celsius": random.randint(-2, 12)},
        {"name": "Anchorage", "country": "USA", "celsius": random.randint(-10, 5)},
        {"name": "Wellington", "country": "New Zealand", "celsius": random.randint(5, 15)},
        {"name": "San Francisco", "country": "USA", "celsius": random.randint(10, 20)},
        {"name": "Vancouver", "country": "Canada", "celsius": random.randint(5, 15)},
        {"name": "Ushuaia", "country": "Argentina", "celsius": random.randint(0, 10)},
        {"name": "Hobart", "country": "Australia", "celsius": random.randint(5, 15)}
    ]
    
    # 按温度排序
    cities.sort(key=lambda x: x["celsius"])
    
    # 生成文本
    cities_text = "\n".join([
        f"{i+1}. {city['name']}, {city['country']}: {city['celsius']}°C ({(city['celsius'] * 9/5) + 32:.1f}°F)"
        for i, city in enumerate(cities[:5])  # 只显示前5个最凉爽的城市
    ])
    
    return f"当前最凉爽的城市:\n{cities_text}"

# 注册更高级的天气工具
@mcp.tool()
async def get_weather_forecast(location: str, days: int = 3) -> str:
    """获取指定位置的天气预报"""
    logger.info(f"获取天气预报: {location}, {days}天")
    
    # 示例实现
    forecasts = {
        "New York": ["晴天，22°C", "多云，24°C", "晴天，23°C", "雨天，20°C", "多云，21°C"],
        "London": ["多云，15°C", "雨天，14°C", "雨天，13°C", "多云，15°C", "晴天，17°C"],
    }
    
    if location in forecasts:
        # 返回请求的天数预报（最多可用天数）
        days = min(days, len(forecasts[location]))
        forecast_text = "\n".join([f"第{i+1}天: {forecasts[location][i]}" for i in range(days)])
        return f"{location}的{days}天预报:\n{forecast_text}"
    else:
        return f"未找到{location}的天气预报"

# 注册天气提醒工具
@mcp.tool()
async def subscribe_weather_alerts(location: str, email: str) -> str:
    """订阅指定位置的天气预警"""
    logger.info(f"订阅天气预警: {location}, {email}")
    
    # 示例实现 - 在实际应用中会将此信息保存到数据库
    return f"成功订阅{location}的天气预警，通知将发送到{email}"

# 主函数
if __name__ == "__main__":
    # 运行MCP服务器
    mcp.run(transport="streamable-http")
