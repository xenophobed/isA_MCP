# Event Service 优化计划

## 🎯 核心原则

Event Service 应该是一个专业的 **Ambient Monitoring Service**：
- 专注于环境感知和事件监控
- 通过 Intelligence Service 增强 AI 分析能力  
- 保持简单、可靠、高性能的监控核心

## 🔧 优化方案

### 1. 增强现有监控能力

#### 1.1 完善 threshold_watch 实现
```python
# 在 event_services.py 中添加
async def _threshold_monitor(self, task: EventSourceTask):
    """Monitor thresholds using Intelligence Service for analysis"""
    config = task.config
    metric_url = config.get("metric_url")
    threshold_value = config.get("threshold")
    comparison = config.get("comparison", "greater_than")  # greater_than, less_than, equals
    
    while self.running and task.status == "active":
        try:
            # 1. 获取数据
            current_value = await self._fetch_metric_data(metric_url)
            
            # 2. 使用 Intelligence Service 分析趋势
            from tools.services.intelligence_service.language.text_summarizer import TextSummarizer
            summarizer = TextSummarizer()
            
            trend_analysis = await summarizer.summarize_text(
                text=f"Metric value changed from {task.last_value} to {current_value}",
                style="technical",
                length="brief"
            )
            
            # 3. 检查阈值
            threshold_breached = self._check_threshold(current_value, threshold_value, comparison)
            
            if threshold_breached:
                feedback = EventFeedback(
                    task_id=task.task_id,
                    event_type="threshold_breach",
                    data={
                        "metric_url": metric_url,
                        "current_value": current_value,
                        "threshold_value": threshold_value,
                        "comparison": comparison,
                        "trend_analysis": trend_analysis.get("summary"),
                        "severity": self._calculate_severity(current_value, threshold_value),
                        "user_id": task.user_id
                    },
                    timestamp=datetime.now(),
                    priority=4  # High priority for threshold breaches
                )
                
                await self._send_feedback(feedback, task.callback_url)
                
            task.last_value = current_value
            task.last_check = datetime.now()
            await asyncio.sleep(config.get("check_interval_minutes", 5) * 60)
            
        except Exception as e:
            logger.error(f"Threshold monitor error for task {task.task_id}: {e}")
            await asyncio.sleep(60)
```

#### 1.2 增强 web_monitor 的智能分析
```python
async def _web_monitor_enhanced(self, task: EventSourceTask):
    """Enhanced web monitoring with Intelligence Service integration"""
    config = task.config
    urls = config.get("urls", [])
    keywords = config.get("keywords", [])
    
    while self.running and task.status == "active":
        try:
            for url in urls:
                content = await self._scrape_web_content(url)
                
                if content:
                    # 1. 使用 Intelligence Service 进行智能内容分析
                    from tools.services.intelligence_service.language.text_summarizer import TextSummarizer
                    from tools.services.intelligence_service.language.text_extractor import TextExtractor
                    
                    summarizer = TextSummarizer()
                    extractor = TextExtractor()
                    
                    # 提取关键信息
                    key_points = await extractor.extract_key_information(
                        text=content,
                        keywords=keywords,
                        context="web content monitoring"
                    )
                    
                    # 生成智能摘要
                    if key_points.get("matches_found"):
                        summary = await summarizer.summarize_text(
                            text=content[:2000],
                            style="executive",
                            length="brief",
                            custom_focus=keywords
                        )
                        
                        # 检查内容变化（现有逻辑）
                        content_hash = hashlib.md5(content.encode()).hexdigest()
                        last_hash = self.last_content_hashes.get(url, "")
                        
                        if content_hash != last_hash:
                            feedback = EventFeedback(
                                task_id=task.task_id,
                                event_type="intelligent_web_change",
                                data={
                                    "url": url,
                                    "content_summary": summary.get("summary"),
                                    "key_points": key_points.get("extracted_info"),
                                    "keywords_found": key_points.get("matched_keywords"),
                                    "change_significance": summary.get("quality_score"),
                                    "description": task.description,
                                    "user_id": task.user_id
                                },
                                timestamp=datetime.now(),
                                priority=3
                            )
                            
                            await self._send_feedback(feedback, task.callback_url)
                            self.last_content_hashes[url] = content_hash
                
            task.last_check = datetime.now()
            await asyncio.sleep(config.get("check_interval_minutes", 30) * 60)
            
        except Exception as e:
            logger.error(f"Enhanced web monitor error for task {task.task_id}: {e}")
            await asyncio.sleep(60)
```

### 2. 新增智能监控任务类型

#### 2.1 图像监控任务
```python
class EventSourceTaskType(Enum):
    WEB_MONITOR = "web_monitor"
    SCHEDULE = "schedule" 
    NEWS_DIGEST = "news_digest"
    THRESHOLD_WATCH = "threshold_watch"
    IMAGE_MONITOR = "image_monitor"  # 新增
    SENTIMENT_MONITOR = "sentiment_monitor"  # 新增

async def _image_monitor(self, task: EventSourceTask):
    """Monitor images from URLs or directories for changes using Vision AI"""
    config = task.config
    image_sources = config.get("image_sources", [])  # URLs or local paths
    analysis_prompt = config.get("analysis_prompt", "Describe any significant changes in this image")
    
    while self.running and task.status == "active":
        try:
            from tools.services.intelligence_service.vision.image_analyzer import ImageAnalyzer
            analyzer = ImageAnalyzer()
            
            for source in image_sources:
                # 获取图像
                if source.startswith("http"):
                    image_data = await self._download_image(source)
                else:
                    image_data = source  # Local path
                
                # 使用 Vision AI 分析
                analysis = await analyzer.analyze(
                    image=image_data,
                    prompt=analysis_prompt
                )
                
                if analysis.success:
                    # 比较与上次分析的差异
                    last_analysis = self.last_image_analysis.get(source, "")
                    
                    if self._significant_change_detected(analysis.response, last_analysis):
                        feedback = EventFeedback(
                            task_id=task.task_id,
                            event_type="image_change_detected",
                            data={
                                "image_source": source,
                                "analysis": analysis.response,
                                "model_used": analysis.model_used,
                                "confidence": "high",  # Could be enhanced with similarity scoring
                                "description": task.description,
                                "user_id": task.user_id
                            },
                            timestamp=datetime.now(),
                            priority=2
                        )
                        
                        await self._send_feedback(feedback, task.callback_url)
                        self.last_image_analysis[source] = analysis.response
                
            await asyncio.sleep(config.get("check_interval_minutes", 60) * 60)
            
        except Exception as e:
            logger.error(f"Image monitor error for task {task.task_id}: {e}")
            await asyncio.sleep(300)
```

#### 2.2 情感监控任务
```python
async def _sentiment_monitor(self, task: EventSourceTask):
    """Monitor sentiment changes in text sources using NLP analysis"""
    config = task.config
    text_sources = config.get("text_sources", [])  # URLs, social media, etc.
    sentiment_threshold = config.get("sentiment_threshold", 0.3)
    
    while self.running and task.status == "active":
        try:
            from tools.services.intelligence_service.language.text_extractor import TextExtractor
            extractor = TextExtractor()
            
            for source in text_sources:
                content = await self._get_text_content(source)
                
                if content:
                    # 使用 Intelligence Service 进行情感分析
                    sentiment_analysis = await extractor.analyze_sentiment(
                        text=content,
                        include_emotion_breakdown=True
                    )
                    
                    current_sentiment = sentiment_analysis.get("sentiment_score", 0)
                    last_sentiment = self.last_sentiment_scores.get(source, 0)
                    
                    # 检查情感变化是否超过阈值
                    sentiment_change = abs(current_sentiment - last_sentiment)
                    
                    if sentiment_change > sentiment_threshold:
                        feedback = EventFeedback(
                            task_id=task.task_id,
                            event_type="sentiment_change",
                            data={
                                "source": source,
                                "current_sentiment": current_sentiment,
                                "previous_sentiment": last_sentiment,
                                "change_magnitude": sentiment_change,
                                "emotion_breakdown": sentiment_analysis.get("emotions"),
                                "key_phrases": sentiment_analysis.get("key_phrases"),
                                "description": task.description,
                                "user_id": task.user_id
                            },
                            timestamp=datetime.now(),
                            priority=3
                        )
                        
                        await self._send_feedback(feedback, task.callback_url)
                        self.last_sentiment_scores[source] = current_sentiment
                
            await asyncio.sleep(config.get("check_interval_minutes", 30) * 60)
            
        except Exception as e:
            logger.error(f"Sentiment monitor error for task {task.task_id}: {e}")
            await asyncio.sleep(300)
```

### 3. 增强事件处理智能化

#### 3.1 智能事件分类和优先级
```python
async def _intelligent_event_processing(self, feedback: EventFeedback):
    """Process events with Intelligence Service for classification and prioritization"""
    try:
        from tools.services.intelligence_service.language.text_generator import TextGenerator
        generator = TextGenerator()
        
        # 生成事件分析提示
        analysis_prompt = f"""
        Analyze this event and provide structured classification:
        
        Event Type: {feedback.event_type}
        Event Data: {json.dumps(feedback.data, indent=2)}
        
        Please provide:
        1. Urgency Level (1-5, where 5 is critical)
        2. Category (technical, business, security, informational)
        3. Recommended Actions (list of specific actions)
        4. Impact Assessment (high/medium/low)
        5. Follow-up Requirements (any required monitoring or actions)
        
        Respond in JSON format.
        """
        
        analysis = await generator.generate_text(
            prompt=analysis_prompt,
            temperature=0.1,  # Low temperature for consistent analysis
            max_tokens=500
        )
        
        if analysis.get("success"):
            try:
                event_intelligence = json.loads(analysis.get("generated_text", "{}"))
                
                # 更新事件优先级和元数据
                feedback.priority = event_intelligence.get("urgency_level", feedback.priority)
                feedback.data["ai_analysis"] = event_intelligence
                feedback.data["processing_timestamp"] = datetime.now().isoformat()
                
                return feedback
                
            except json.JSONDecodeError:
                logger.warning("Failed to parse AI event analysis as JSON")
                
    except Exception as e:
        logger.error(f"Error in intelligent event processing: {e}")
    
    return feedback
```

### 4. 新增 MCP 工具

#### 4.1 智能任务创建助手
```python
@mcp.tool()
async def create_intelligent_task(
    task_description: str,
    monitoring_targets: list,
    user_id: str = "default"
) -> str:
    """
    Create intelligent monitoring tasks using AI analysis
    
    Analyzes the task description and targets to automatically configure
    the best monitoring approach using Intelligence Service capabilities.
    """
    try:
        from tools.services.intelligence_service.language.text_generator import TextGenerator
        generator = TextGenerator()
        
        # 分析任务需求
        analysis_prompt = f"""
        Analyze this monitoring request and suggest the optimal configuration:
        
        Task Description: {task_description}
        Monitoring Targets: {monitoring_targets}
        
        Based on the description and targets, suggest:
        1. Best task type (web_monitor, image_monitor, sentiment_monitor, threshold_watch, schedule)
        2. Optimal configuration parameters
        3. Recommended check intervals
        4. Priority level
        5. Keywords or analysis prompts
        
        Respond with a JSON configuration that can be used directly.
        """
        
        suggestion = await generator.generate_text(
            prompt=analysis_prompt,
            temperature=0.2,
            max_tokens=800
        )
        
        if suggestion.get("success"):
            try:
                config = json.loads(suggestion.get("generated_text", "{}"))
                
                # 创建智能推荐的任务
                result = await tools.task_service.create_task({
                    "task_type": config.get("task_type"),
                    "description": task_description,
                    "config": config.get("configuration", {}),
                    "user_id": user_id
                })
                
                return json.dumps({
                    "status": "success",
                    "task_id": result.get("task_id"),
                    "ai_recommendation": config,
                    "message": f"Intelligent task created based on AI analysis",
                    "timestamp": datetime.now().isoformat()
                })
                
            except json.JSONDecodeError:
                logger.warning("Failed to parse AI task suggestion")
                
    except Exception as e:
        logger.error(f"Error in intelligent task creation: {e}")
        
    return json.dumps({
        "status": "error",
        "message": "Failed to create intelligent task",
        "timestamp": datetime.now().isoformat()
    })
```

#### 4.2 事件趋势分析工具
```python
@mcp.tool()
async def analyze_event_trends(
    user_id: str,
    time_period: str = "7d",  # 7d, 30d, 90d
    event_types: list = None
) -> str:
    """
    Analyze event trends using Intelligence Service
    
    Provides intelligent analysis of event patterns, anomalies, and insights
    using historical event data and AI-powered trend analysis.
    """
    try:
        # 获取历史事件数据
        events = await tools.event_service_logic.get_user_events(
            user_id=user_id,
            time_period=time_period,
            event_types=event_types
        )
        
        if not events:
            return json.dumps({
                "status": "success",
                "message": "No events found for analysis",
                "trends": {}
            })
        
        # 使用 Intelligence Service 分析趋势
        from tools.services.intelligence_service.language.text_summarizer import TextSummarizer
        summarizer = TextSummarizer()
        
        # 构建分析数据
        event_summary = f"""
        Event Analysis Data for User {user_id}:
        
        Total Events: {len(events)}
        Time Period: {time_period}
        Event Types: {list(set([e.get('event_type') for e in events]))}
        
        Event Distribution:
        {json.dumps([{
            'type': e.get('event_type'),
            'timestamp': e.get('created_at'),
            'priority': e.get('priority', 1)
        } for e in events], indent=2)}
        """
        
        # AI 趋势分析
        trend_analysis = await summarizer.summarize_text(
            text=event_summary,
            style="analytical",
            length="detailed",
            custom_focus=["patterns", "anomalies", "trends", "insights"]
        )
        
        return json.dumps({
            "status": "success",
            "trends": {
                "summary": trend_analysis.get("summary"),
                "key_insights": trend_analysis.get("key_points"),
                "event_count": len(events),
                "time_period": time_period,
                "patterns_detected": trend_analysis.get("patterns", []),
                "recommendations": trend_analysis.get("recommendations", [])
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in event trend analysis: {e}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to analyze event trends: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })
```

## 🎯 实施优先级

### Phase 1: 核心增强 (1-2 weeks)
1. ✅ 完善 `threshold_watch` 实现
2. ✅ 增强现有 `web_monitor` 的智能分析
3. ✅ 集成 Intelligence Service 到事件处理流程

### Phase 2: 智能监控 (2-3 weeks)  
1. ✅ 新增 `image_monitor` 任务类型
2. ✅ 新增 `sentiment_monitor` 任务类型
3. ✅ 智能事件分类和优先级系统

### Phase 3: 高级功能 (1-2 weeks)
1. ✅ 智能任务创建助手工具
2. ✅ 事件趋势分析工具
3. ✅ 更新文档和测试

## 🎭 保持的原则

1. **专注核心职责**: Event Service 仍然是监控服务，不是执行引擎
2. **原子化集成**: Intelligence Service 提供离散的 AI 能力
3. **向后兼容**: 现有任务和工具继续工作
4. **性能优先**: AI 增强不应显著影响监控性能
5. **错误隔离**: AI 失败不应影响基础监控功能

这样，Event Service 就从简单的监控服务进化为 **Intelligent Ambient Monitoring Service**，既保持了专业的监控能力，又通过 Intelligence Service 获得了强大的 AI 分析能力！