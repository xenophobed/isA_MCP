#!/usr/bin/env python3
"""
用户行为ML分析器 - 集成现有的ML模型服务分析用户时间行为模式
Gold Data -> ML Analysis -> Structured Insights (为Persona生成准备)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
import json

from core.logging import get_logger
from core.database import get_supabase_client
from tools.services.data_analytics_service.processors.data_processors.model.time_series_processor import TimeSeriesProcessor

logger = get_logger(__name__)

class UserBehaviorMLAnalyzer:
    """
    用户行为ML分析器
    
    功能：
    1. 从Gold Data创建时间序列数据
    2. 使用现有的TimeSeriesProcessor分析用户行为模式
    3. 生成结构化的行为洞察
    4. 为Persona生成提供ML驱动的用户特征
    """
    
    def __init__(self):
        self.db_client = get_supabase_client()
        self.ts_processor = None  # 延迟初始化
        
    async def analyze_user_behavior_patterns(self, user_id: str) -> Dict[str, Any]:
        """分析单个用户的行为模式 - ML驱动的深度分析"""
        try:
            logger.info(f"🧠 Starting ML behavior analysis for user: {user_id}")
            
            # 1. 从数据库收集时间序列数据
            time_series_data = await self._collect_user_time_series_data(user_id)
            
            if not time_series_data or len(time_series_data) < 7:  # 至少需要7天数据
                logger.warning(f"⚠️ Insufficient time series data for user {user_id}")
                return self._generate_minimal_analysis()
            
            # 2. 准备ML分析数据
            df = self._prepare_ml_dataframe(time_series_data)
            
            # 3. 执行时间序列ML分析
            ml_results = await self._run_ml_time_series_analysis(df)
            
            # 4. 分析用户活动模式（什么时间做什么）
            activity_patterns = await self._analyze_time_activity_correlation(user_id, df)
            
            # 5. 生成ML驱动的用户特征
            ml_features = self._generate_ml_user_features(ml_results, activity_patterns)
            
            # 6. 组装完整的ML分析结果
            analysis_result = {
                "user_id": user_id,
                "analysis_timestamp": datetime.now().isoformat(),
                "data_points": len(time_series_data),
                "analysis_period_days": self._calculate_analysis_period(time_series_data),
                
                # ML时间序列分析结果
                "time_series_insights": ml_results,
                
                # 时间-活动相关性分析
                "activity_patterns": activity_patterns,
                
                # ML生成的用户特征（用于Persona）
                "ml_user_features": ml_features,
                
                # 分析质量指标
                "analysis_quality": {
                    "data_completeness": min(1.0, len(time_series_data) / 30),
                    "pattern_confidence": ml_features.get("pattern_confidence", 0.5),
                    "prediction_accuracy": ml_results.get("forecast_accuracy", 0.5)
                }
            }
            
            logger.info(f"✅ ML behavior analysis completed for user: {user_id}")
            logger.info(f"📊 Generated {len(ml_features)} ML features and {len(activity_patterns)} activity patterns")
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"❌ ML behavior analysis failed for user {user_id}: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e), "user_id": user_id}
    
    async def _collect_user_time_series_data(self, user_id: str) -> List[Dict]:
        """收集用户的时间序列数据"""
        try:
            time_series_data = []
            
            # 从sessions获取活动时间点
            sessions_response = self.db_client.table('sessions')\
                .select('created_at, duration, id')\
                .eq('user_id', user_id)\
                .order('created_at', desc=False)\
                .execute()
            
            if sessions_response.data:
                for session in sessions_response.data:
                    if session.get('created_at'):
                        time_series_data.append({
                            'timestamp': session['created_at'],
                            'activity_type': 'session_start',
                            'value': 1,  # 会话开始事件
                            'duration': session.get('duration', 0),
                            'source': 'sessions',
                            'source_id': session['id']
                        })
            
            # 从session_messages获取消息时间点
            messages_response = self.db_client.table('session_messages')\
                .select('created_at, content, session_id')\
                .eq('user_id', user_id)\
                .order('created_at', desc=False)\
                .limit(200)\
                .execute()
            
            if messages_response.data:
                for message in messages_response.data:
                    if message.get('created_at') and message.get('content'):
                        # 根据内容长度推断活动强度
                        content_length = len(message['content'])
                        activity_intensity = min(1.0, content_length / 500)  # 归一化到0-1
                        
                        time_series_data.append({
                            'timestamp': message['created_at'],
                            'activity_type': 'message',
                            'value': activity_intensity,
                            'content_length': content_length,
                            'source': 'session_messages',
                            'session_id': message.get('session_id')
                        })
            
            # 从user_events获取行为事件
            events_response = self.db_client.table('user_events')\
                .select('timestamp, event_name, properties')\
                .eq('user_id', user_id)\
                .order('timestamp', desc=False)\
                .execute()
            
            if events_response.data:
                for event in events_response.data:
                    if event.get('timestamp'):
                        time_series_data.append({
                            'timestamp': event['timestamp'],
                            'activity_type': event.get('event_name', 'unknown_event'),
                            'value': 0.5,  # 事件权重
                            'source': 'user_events',
                            'properties': event.get('properties', {})
                        })
            
            # 按时间排序
            time_series_data.sort(key=lambda x: x['timestamp'])
            
            logger.info(f"📊 Collected {len(time_series_data)} time series data points for user {user_id}")
            return time_series_data
            
        except Exception as e:
            logger.error(f"❌ Failed to collect time series data for user {user_id}: {e}")
            return []
    
    def _prepare_ml_dataframe(self, time_series_data: List[Dict]) -> pd.DataFrame:
        """准备ML分析用的DataFrame"""
        try:
            if not time_series_data:
                return pd.DataFrame()
            
            # 转换为DataFrame
            df = pd.DataFrame(time_series_data)
            
            # 处理时间戳
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
            
            # 按小时聚合活动强度
            df_hourly = df.groupby([
                df.index.date,
                df.index.hour
            ]).agg({
                'value': 'sum',  # 总活动强度
                'activity_type': 'count'  # 活动次数
            }).reset_index()
            
            # 重新构建时间索引
            df_hourly['datetime'] = pd.to_datetime(
                df_hourly['level_0'].astype(str) + ' ' + 
                df_hourly['level_1'].astype(str) + ':00:00'
            )
            df_hourly = df_hourly.set_index('datetime')
            df_hourly = df_hourly.drop(['level_0', 'level_1'], axis=1)
            
            # 重命名列
            df_hourly.columns = ['activity_intensity', 'activity_count']
            
            # 填充缺失时间点为0
            full_range = pd.date_range(
                start=df_hourly.index.min(),
                end=df_hourly.index.max(),
                freq='H'
            )
            df_hourly = df_hourly.reindex(full_range, fill_value=0)
            
            logger.info(f"📈 Prepared ML DataFrame with {len(df_hourly)} hourly data points")
            return df_hourly
            
        except Exception as e:
            logger.error(f"❌ Failed to prepare ML dataframe: {e}")
            return pd.DataFrame()
    
    async def _run_ml_time_series_analysis(self, df: pd.DataFrame) -> Dict[str, Any]:
        """运行ML时间序列分析 - 使用现有的TimeSeriesProcessor"""
        try:
            if df.empty or len(df) < 7:
                return {"error": "insufficient_data"}
            
            # 初始化TimeSeriesProcessor (如果还没初始化)
            if self.ts_processor is None:
                # 将DataFrame保存为临时CSV用于TimeSeriesProcessor
                import tempfile
                import os
                
                temp_dir = tempfile.mkdtemp()
                csv_path = os.path.join(temp_dir, "user_behavior_timeseries.csv")
                
                # 准备TimeSeriesProcessor需要的格式
                ts_df = df.reset_index()
                ts_df.columns = ['ds', 'y', 'activity_count']  # Prophet格式
                ts_df.to_csv(csv_path, index=False)
                
                # 初始化处理器
                self.ts_processor = TimeSeriesProcessor(file_path=csv_path)
            
            ml_results = {}
            
            # 1. 检测季节性模式
            try:
                if len(df) >= 24:  # 至少需要24小时数据
                    seasonality_results = self.ts_processor.detect_seasonality('y')
                    ml_results['seasonality'] = seasonality_results
                    logger.info("✅ Seasonality detection completed")
            except Exception as e:
                logger.warning(f"⚠️ Seasonality detection failed: {e}")
            
            # 2. 季节性分解
            try:
                if len(df) >= 48:  # 至少需要48小时数据进行分解
                    decomposition_results = self.ts_processor.seasonal_decomposition('y', period=24)
                    ml_results['decomposition'] = decomposition_results
                    logger.info("✅ Seasonal decomposition completed")
            except Exception as e:
                logger.warning(f"⚠️ Seasonal decomposition failed: {e}")
            
            # 3. 预测 (如果数据足够)
            try:
                if len(df) >= 72:  # 至少需要3天数据进行预测
                    forecast_results = self.ts_processor.prophet_forecast('y', periods=24)  # 预测24小时
                    ml_results['forecast'] = forecast_results
                    logger.info("✅ Prophet forecasting completed")
            except Exception as e:
                logger.warning(f"⚠️ Prophet forecasting failed: {e}")
                # 如果Prophet失败，尝试简单的指数平滑
                try:
                    forecast_results = self.ts_processor.exponential_smoothing_forecast('y', periods=24)
                    ml_results['forecast'] = forecast_results
                    logger.info("✅ Exponential smoothing forecasting completed")
                except Exception as e2:
                    logger.warning(f"⚠️ All forecasting methods failed: {e2}")
            
            # 4. 综合分析
            if ml_results:
                try:
                    comprehensive_results = self.ts_processor.comprehensive_time_series_analysis(
                        'ds', 'y', periods=24
                    )
                    ml_results['comprehensive'] = comprehensive_results
                    logger.info("✅ Comprehensive analysis completed")
                except Exception as e:
                    logger.warning(f"⚠️ Comprehensive analysis failed: {e}")
            
            return ml_results
            
        except Exception as e:
            logger.error(f"❌ ML time series analysis failed: {e}")
            return {"error": str(e)}
    
    async def _analyze_time_activity_correlation(self, user_id: str, df: pd.DataFrame) -> Dict[str, Any]:
        """分析时间-活动相关性：用户在什么时间习惯做什么"""
        try:
            if df.empty:
                return {}
            
            activity_patterns = {}
            
            # 1. 按小时分析活动模式
            hourly_patterns = df.groupby(df.index.hour).agg({
                'activity_intensity': ['mean', 'std', 'count'],
                'activity_count': 'mean'
            }).round(3)
            
            # 扁平化列名
            hourly_patterns.columns = [
                'avg_intensity', 'std_intensity', 'total_periods', 'avg_count'
            ]
            
            # 识别高峰时段
            mean_intensity = hourly_patterns['avg_intensity'].mean()
            peak_hours = hourly_patterns[
                hourly_patterns['avg_intensity'] > mean_intensity * 1.2
            ].index.tolist()
            
            activity_patterns['peak_hours'] = peak_hours
            activity_patterns['hourly_patterns'] = hourly_patterns.to_dict()
            
            # 2. 按星期几分析
            daily_patterns = df.groupby(df.index.dayofweek).agg({
                'activity_intensity': 'mean',
                'activity_count': 'mean'
            }).round(3)
            
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            daily_patterns.index = [day_names[i] for i in daily_patterns.index]
            
            activity_patterns['weekly_patterns'] = daily_patterns.to_dict()
            
            # 3. 获取具体的活动内容分析
            content_patterns = await self._analyze_time_specific_content(user_id, peak_hours)
            activity_patterns['content_patterns'] = content_patterns
            
            # 4. 生成行为模式摘要
            behavior_summary = self._generate_behavior_summary(hourly_patterns, daily_patterns, peak_hours)
            activity_patterns['behavior_summary'] = behavior_summary
            
            logger.info(f"📊 Activity pattern analysis completed: {len(peak_hours)} peak hours identified")
            return activity_patterns
            
        except Exception as e:
            logger.error(f"❌ Time-activity correlation analysis failed: {e}")
            return {}
    
    async def _analyze_time_specific_content(self, user_id: str, peak_hours: List[int]) -> Dict[str, Any]:
        """分析特定时间段用户在做什么具体内容"""
        try:
            content_patterns = {}
            
            if not peak_hours:
                return content_patterns
            
            # 获取高峰时段的消息内容
            for hour in peak_hours:
                try:
                    # 构建SQL查询条件：获取该小时的消息
                    messages_response = self.db_client.table('session_messages')\
                        .select('content, created_at')\
                        .eq('user_id', user_id)\
                        .execute()
                    
                    if not messages_response.data:
                        continue
                    
                    # 过滤该小时的消息
                    hour_messages = []
                    for msg in messages_response.data:
                        if msg.get('created_at'):
                            try:
                                msg_time = datetime.fromisoformat(msg['created_at'].replace('Z', '+00:00'))
                                if msg_time.hour == hour and msg.get('content'):
                                    hour_messages.append(msg['content'])
                            except:
                                continue
                    
                    if hour_messages:
                        # 简单的关键词分析
                        all_content = ' '.join(hour_messages).lower()
                        
                        # 识别主要活动类型
                        activity_keywords = {
                            'coding': ['code', 'function', 'python', 'javascript', 'debug', 'error', 'script'],
                            'learning': ['learn', 'understand', 'explain', 'how to', 'what is', 'tutorial'],
                            'data_analysis': ['data', 'analysis', 'pandas', 'dataframe', 'sql', 'chart'],
                            'problem_solving': ['help', 'issue', 'problem', 'fix', 'solve', 'error'],
                            'planning': ['plan', 'organize', 'schedule', 'todo', 'project', 'task']
                        }
                        
                        hour_activities = {}
                        for activity, keywords in activity_keywords.items():
                            count = sum(1 for keyword in keywords if keyword in all_content)
                            if count > 0:
                                hour_activities[activity] = count
                        
                        if hour_activities:
                            # 找出主要活动
                            main_activity = max(hour_activities.items(), key=lambda x: x[1])[0]
                            content_patterns[f"hour_{hour}"] = {
                                'main_activity': main_activity,
                                'activity_scores': hour_activities,
                                'message_count': len(hour_messages),
                                'avg_message_length': sum(len(msg) for msg in hour_messages) / len(hour_messages)
                            }
                
                except Exception as e:
                    logger.warning(f"⚠️ Failed to analyze content for hour {hour}: {e}")
                    continue
            
            return content_patterns
            
        except Exception as e:
            logger.error(f"❌ Time-specific content analysis failed: {e}")
            return {}
    
    def _generate_behavior_summary(self, hourly_patterns: pd.DataFrame, 
                                 daily_patterns: pd.DataFrame, peak_hours: List[int]) -> Dict[str, str]:
        """生成行为模式摘要"""
        try:
            summary = {}
            
            # 分析工作模式
            if peak_hours:
                morning_hours = [h for h in peak_hours if 6 <= h <= 11]
                afternoon_hours = [h for h in peak_hours if 12 <= h <= 17]
                evening_hours = [h for h in peak_hours if 18 <= h <= 23]
                night_hours = [h for h in peak_hours if h >= 0 and h <= 5]
                
                if len(morning_hours) >= 2:
                    summary['work_pattern'] = 'morning_person'
                elif len(evening_hours) >= 2 or len(night_hours) >= 1:
                    summary['work_pattern'] = 'night_owl'
                elif len(afternoon_hours) >= 2:
                    summary['work_pattern'] = 'afternoon_focused'
                else:
                    summary['work_pattern'] = 'flexible'
            
            # 分析活动强度
            if not hourly_patterns.empty:
                max_intensity = hourly_patterns['avg_intensity'].max()
                if max_intensity > 2.0:
                    summary['intensity_level'] = 'high_intensity'
                elif max_intensity > 1.0:
                    summary['intensity_level'] = 'moderate_intensity'
                else:
                    summary['intensity_level'] = 'light_usage'
            
            # 分析一致性
            if not hourly_patterns.empty:
                intensity_std = hourly_patterns['avg_intensity'].std()
                if intensity_std < 0.5:
                    summary['consistency'] = 'highly_consistent'
                elif intensity_std < 1.0:
                    summary['consistency'] = 'moderately_consistent'
                else:
                    summary['consistency'] = 'variable_pattern'
            
            return summary
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to generate behavior summary: {e}")
            return {}
    
    def _generate_ml_user_features(self, ml_results: Dict[str, Any], 
                                 activity_patterns: Dict[str, Any]) -> Dict[str, Any]:
        """基于ML分析结果生成用户特征（用于Persona生成）"""
        try:
            ml_features = {}
            
            # 1. 时间行为特征
            if activity_patterns.get('peak_hours'):
                ml_features['peak_activity_hours'] = activity_patterns['peak_hours']
                ml_features['primary_work_pattern'] = activity_patterns.get('behavior_summary', {}).get('work_pattern', 'flexible')
            
            # 2. 活动强度特征
            behavior_summary = activity_patterns.get('behavior_summary', {})
            ml_features['usage_intensity'] = behavior_summary.get('intensity_level', 'moderate_intensity')
            ml_features['behavior_consistency'] = behavior_summary.get('consistency', 'moderately_consistent')
            
            # 3. 季节性特征（来自ML分析）
            if ml_results.get('seasonality'):
                seasonality = ml_results['seasonality']
                if seasonality.get('has_weekly_seasonality'):
                    ml_features['weekly_patterns_detected'] = True
                if seasonality.get('has_daily_seasonality'):
                    ml_features['daily_patterns_detected'] = True
            
            # 4. 预测特征（来自ML分析）
            if ml_results.get('forecast'):
                forecast = ml_results['forecast']
                if forecast.get('trend'):
                    ml_features['activity_trend'] = forecast['trend']
                if forecast.get('forecast_accuracy'):
                    ml_features['predictability_score'] = forecast['forecast_accuracy']
            
            # 5. 内容活动特征
            content_patterns = activity_patterns.get('content_patterns', {})
            if content_patterns:
                # 统计各时间段的主要活动
                main_activities = [pattern.get('main_activity') for pattern in content_patterns.values()]
                if main_activities:
                    from collections import Counter
                    activity_counts = Counter(main_activities)
                    ml_features['dominant_activity_type'] = activity_counts.most_common(1)[0][0]
                    ml_features['activity_diversity'] = len(set(main_activities)) / len(main_activities)
            
            # 6. 计算整体模式置信度
            pattern_indicators = [
                bool(ml_features.get('peak_activity_hours')),
                bool(ml_features.get('weekly_patterns_detected')),
                bool(ml_features.get('dominant_activity_type')),
                bool(ml_results.get('seasonality')),
                bool(ml_results.get('forecast'))
            ]
            
            ml_features['pattern_confidence'] = sum(pattern_indicators) / len(pattern_indicators)
            
            logger.info(f"🎯 Generated {len(ml_features)} ML user features")
            return ml_features
            
        except Exception as e:
            logger.error(f"❌ Failed to generate ML user features: {e}")
            return {}
    
    def _generate_minimal_analysis(self) -> Dict[str, Any]:
        """生成最小化分析结果（数据不足时）"""
        return {
            "analysis_timestamp": datetime.now().isoformat(),
            "data_points": 0,
            "status": "insufficient_data",
            "ml_user_features": {
                "usage_intensity": "unknown",
                "behavior_consistency": "unknown",
                "primary_work_pattern": "unknown",
                "pattern_confidence": 0.0
            },
            "activity_patterns": {},
            "time_series_insights": {}
        }
    
    def _calculate_analysis_period(self, time_series_data: List[Dict]) -> int:
        """计算分析时间段的天数"""
        if not time_series_data:
            return 0
        
        try:
            timestamps = [datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00')) 
                         for item in time_series_data]
            return (max(timestamps) - min(timestamps)).days + 1
        except:
            return 0

# 全局实例
user_behavior_ml_analyzer = UserBehaviorMLAnalyzer()

# 便捷函数
async def analyze_user_ml_behavior(user_id: str) -> Dict[str, Any]:
    """分析用户的ML驱动行为模式"""
    return await user_behavior_ml_analyzer.analyze_user_behavior_patterns(user_id)