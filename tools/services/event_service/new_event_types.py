#!/usr/bin/env python3
"""
New Event Service Types
Enhanced event monitoring with Intelligence Service integration
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import asyncio
import aiohttp
from dataclasses import dataclass

class NewEventTaskType(Enum):
    """New enhanced event task types"""
    # 事件触发任务
    NEWS_MONITOR = "news_monitor"           # 新闻监控
    WEATHER_ALERT = "weather_alert"         # 天气预警  
    PRICE_TRACKER = "price_tracker"         # 电商价格跟踪
    STOCK_MONITOR = "stock_monitor"         # 股票监控
    SOCIAL_SENTIMENT = "social_sentiment"   # 社交媒体情感监控
    
    # 定时任务
    DAILY_WEATHER = "daily_weather"         # 每日天气
    DAILY_NEWS = "daily_news"               # 每日新闻
    WEEKLY_SUMMARY = "weekly_summary"       # 周总结
    MONTHLY_REPORT = "monthly_report"       # 月报告
    CUSTOM_SCHEDULE = "custom_schedule"     # 自定义定时

@dataclass
class TaskConfig:
    """任务配置基类"""
    pass

@dataclass  
class NewsMonitorConfig(TaskConfig):
    """新闻监控配置"""
    keywords: List[str]                     # 关键词
    sources: List[str]                      # 新闻源
    language: str = "zh"                    # 语言
    urgency_threshold: float = 0.7          # 紧急度阈值
    check_interval_minutes: int = 30        # 检查间隔

@dataclass
class WeatherAlertConfig(TaskConfig):
    """天气预警配置"""
    location: str                           # 位置
    alert_types: List[str]                  # 预警类型 ['rain', 'temperature', 'wind']
    temperature_threshold: Dict[str, float] # 温度阈值 {'min': 0, 'max': 35}
    check_interval_minutes: int = 60        # 检查间隔

@dataclass
class PriceTrackerConfig(TaskConfig):
    """价格跟踪配置"""
    product_urls: List[str]                 # 商品URL列表
    target_price: Optional[float] = None    # 目标价格
    price_drop_threshold: float = 0.1       # 降价阈值(10%)
    check_interval_minutes: int = 120       # 检查间隔

@dataclass
class StockMonitorConfig(TaskConfig):
    """股票监控配置"""
    symbols: List[str]                      # 股票代码
    price_change_threshold: float = 0.05    # 价格变动阈值(5%)
    volume_threshold: Optional[float] = None # 成交量阈值
    check_interval_minutes: int = 15        # 检查间隔

@dataclass
class SocialSentimentConfig(TaskConfig):
    """社交媒体情感监控配置"""
    keywords: List[str]                     # 监控关键词
    platforms: List[str]                    # 平台 ['twitter', 'weibo', 'reddit']
    sentiment_threshold: float = 0.3        # 情感变化阈值
    check_interval_minutes: int = 60        # 检查间隔

@dataclass
class DailyWeatherConfig(TaskConfig):
    """每日天气配置"""
    location: str                           # 位置
    notification_time: str = "08:00"        # 通知时间
    include_forecast: bool = True           # 包含预报
    include_aqi: bool = True                # 包含空气质量

@dataclass
class DailyNewsConfig(TaskConfig):
    """每日新闻配置"""
    categories: List[str]                   # 新闻分类
    sources: List[str]                      # 新闻源
    notification_time: str = "08:00"        # 通知时间
    max_articles: int = 10                  # 最大文章数
    language: str = "zh"                    # 语言

@dataclass
class WeeklySummaryConfig(TaskConfig):
    """周总结配置"""
    summary_types: List[str]                # 总结类型 ['news', 'weather', 'tasks']
    notification_time: str = "09:00"        # 通知时间
    day_of_week: int = 0                    # 周几 (0=Monday)

@dataclass
class MonthlyReportConfig(TaskConfig):
    """月报告配置"""
    report_types: List[str]                 # 报告类型
    notification_time: str = "09:00"        # 通知时间
    day_of_month: int = 1                   # 月份中的第几天

@dataclass
class CustomScheduleConfig(TaskConfig):
    """自定义定时配置"""
    schedule_type: str                      # 'cron', 'interval', 'specific_times'
    cron_expression: Optional[str] = None   # Cron表达式
    interval_minutes: Optional[int] = None  # 间隔分钟
    specific_times: Optional[List[str]] = None # 具体时间
    action_type: str = "notification"       # 动作类型
    action_config: Dict[str, Any] = None    # 动作配置

# 示例任务配置
TASK_CONFIG_EXAMPLES = {
    "news_monitor": NewsMonitorConfig(
        keywords=["人工智能", "AI", "机器学习"],
        sources=["tech.sina.com.cn", "36kr.com", "ithome.com"],
        urgency_threshold=0.8,
        check_interval_minutes=30
    ),
    
    "weather_alert": WeatherAlertConfig(
        location="北京市",
        alert_types=["rain", "temperature", "air_quality"],
        temperature_threshold={"min": -5, "max": 35},
        check_interval_minutes=60
    ),
    
    "price_tracker": PriceTrackerConfig(
        product_urls=[
            "https://item.jd.com/100012043978.html",
            "https://detail.tmall.com/item.htm?id=example"
        ],
        target_price=299.0,
        price_drop_threshold=0.15,
        check_interval_minutes=120
    ),
    
    "stock_monitor": StockMonitorConfig(
        symbols=["AAPL", "TSLA", "000001.SZ"],
        price_change_threshold=0.03,
        check_interval_minutes=15
    ),
    
    "daily_weather": DailyWeatherConfig(
        location="上海市",
        notification_time="07:30",
        include_forecast=True,
        include_aqi=True
    ),
    
    "daily_news": DailyNewsConfig(
        categories=["科技", "财经", "国际"],
        sources=["人民日报", "新华社", "科技日报"],
        notification_time="08:00",
        max_articles=8
    ),
    
    "custom_schedule": CustomScheduleConfig(
        schedule_type="cron",
        cron_expression="0 9 * * MON",  # 每周一9点
        action_type="weekly_report",
        action_config={"report_types": ["task_summary", "event_analysis"]}
    )
}

# 任务类型到配置类的映射
TASK_CONFIG_MAPPING = {
    NewEventTaskType.NEWS_MONITOR: NewsMonitorConfig,
    NewEventTaskType.WEATHER_ALERT: WeatherAlertConfig,
    NewEventTaskType.PRICE_TRACKER: PriceTrackerConfig,
    NewEventTaskType.STOCK_MONITOR: StockMonitorConfig,
    NewEventTaskType.SOCIAL_SENTIMENT: SocialSentimentConfig,
    NewEventTaskType.DAILY_WEATHER: DailyWeatherConfig,
    NewEventTaskType.DAILY_NEWS: DailyNewsConfig,
    NewEventTaskType.WEEKLY_SUMMARY: WeeklySummaryConfig,
    NewEventTaskType.MONTHLY_REPORT: MonthlyReportConfig,
    NewEventTaskType.CUSTOM_SCHEDULE: CustomScheduleConfig,
}

def create_task_config(task_type: NewEventTaskType, config_data: Dict[str, Any]) -> TaskConfig:
    """根据任务类型创建配置对象"""
    config_class = TASK_CONFIG_MAPPING.get(task_type)
    if not config_class:
        raise ValueError(f"Unknown task type: {task_type}")
    
    return config_class(**config_data)

def validate_task_config(task_type: NewEventTaskType, config_data: Dict[str, Any]) -> Dict[str, Any]:
    """验证任务配置"""
    try:
        config = create_task_config(task_type, config_data)
        return {"valid": True, "config": config, "error": None}
    except Exception as e:
        return {"valid": False, "config": None, "error": str(e)}