"""
Compliance Risk Predictor

Predicts compliance and security risks based on user behavior patterns
Maps to predict_compliance_risks MCP tool
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import logging
import statistics

from ...prediction_models import ComplianceRiskPrediction, PredictionConfidenceLevel
from ..utilities.risk_assessment_utils import RiskAssessmentUtils
from ..utilities.compliance_monitoring_utils import ComplianceMonitoringUtils

# Import user service repositories
from tools.services.user_service.repositories.usage_repository import UsageRepository
from tools.services.user_service.repositories.session_repository import SessionRepository
from tools.services.user_service.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class ComplianceRiskPredictor:
    """
    Predicts compliance and security risks based on user behavior analysis
    Identifies potential violations, security concerns, and governance issues
    """
    
    def __init__(self):
        """Initialize repositories and utilities"""
        self.usage_repository = UsageRepository()
        self.session_repository = SessionRepository()
        self.user_repository = UserRepository()
        self.risk_utils = RiskAssessmentUtils()
        self.compliance_utils = ComplianceMonitoringUtils()
        
        # Risk indicators by category
        self.risk_indicators = {
            "data_access": {
                "high_risk": ["admin", "delete", "export", "bulk", "privileged"],
                "medium_risk": ["modify", "update", "batch", "query_all"],
                "keywords": ["data", "database", "query", "export", "download"]
            },
            "security": {
                "high_risk": ["bypass", "override", "disable", "escalate", "sudo"],
                "medium_risk": ["access", "auth", "login", "session", "token"],
                "keywords": ["security", "auth", "permission", "access", "login"]
            },
            "compliance": {
                "high_risk": ["gdpr", "hipaa", "pii", "sensitive", "confidential"],
                "medium_risk": ["personal", "private", "restricted", "internal"],
                "keywords": ["compliance", "regulation", "policy", "audit", "governance"]
            },
            "usage_patterns": {
                "high_risk": ["unusual", "after_hours", "excessive", "anomaly"],
                "medium_risk": ["frequent", "bulk", "automated", "scheduled"],
                "keywords": ["pattern", "behavior", "usage", "activity"]
            }
        }
        
        # Compliance frameworks
        self.compliance_frameworks = {
            "gdpr": {"weight": 0.3, "critical_areas": ["data_processing", "consent", "privacy"]},
            "hipaa": {"weight": 0.25, "critical_areas": ["healthcare_data", "patient_info"]},
            "sox": {"weight": 0.2, "critical_areas": ["financial_data", "audit_trail"]},
            "iso27001": {"weight": 0.15, "critical_areas": ["security", "risk_management"]},
            "pci_dss": {"weight": 0.1, "critical_areas": ["payment_data", "card_info"]}
        }
        
        logger.info("Compliance Risk Predictor initialized")
    
    async def predict_risks(
        self, 
        user_id: str, 
        compliance_context: Dict[str, Any],
        timeframe: str
    ) -> ComplianceRiskPrediction:
        """
        Predict compliance risks for a user
        
        Args:
            user_id: User identifier
            compliance_context: Compliance and security context
            timeframe: Analysis timeframe
            
        Returns:
            ComplianceRiskPrediction: Risk assessment with scores and recommendations
        """
        try:
            logger.info(f"Predicting compliance risks for user {user_id}, timeframe: {timeframe}")
            
            # Get historical data from real database
            start_date, end_date = self._parse_timeframe(timeframe)
            
            usage_records = await self.usage_repository.get_user_usage_history(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                limit=2000
            )
            
            sessions = await self.session_repository.get_user_sessions(
                user_id=user_id,
                limit=100
            )
            
            try:
                user_profile = await self.user_repository.get_by_id(user_id)
            except:
                user_profile = None
            
            logger.info(f"Retrieved {len(usage_records)} usage records and {len(sessions)} sessions")
            
            # Analyze risk factors
            risk_factors = await self._analyze_risk_factors(
                usage_records, sessions, compliance_context
            )
            
            # Calculate compliance score
            compliance_score = await self._calculate_compliance_score(
                usage_records, sessions, compliance_context, risk_factors
            )
            
            # Calculate security score
            security_score = await self._calculate_security_score(
                usage_records, sessions, user_profile, risk_factors
            )
            
            # Calculate data governance score
            data_governance_score = await self._calculate_data_governance_score(
                usage_records, compliance_context, risk_factors
            )
            
            # Determine overall risk level
            overall_risk_level = self._determine_risk_level(
                compliance_score, security_score, data_governance_score
            )
            
            # Generate mitigation recommendations
            mitigation_recommendations = await self._generate_mitigation_recommendations(
                risk_factors, compliance_score, security_score, data_governance_score
            )
            
            # Identify violations and alerts
            violations = self._identify_potential_violations(
                usage_records, sessions, compliance_context
            )
            
            # Calculate prediction confidence
            confidence = self._calculate_confidence(
                usage_records, sessions, compliance_context, timeframe
            )
            
            return ComplianceRiskPrediction(
                user_id=user_id,
                confidence=confidence,
                confidence_level=self._determine_confidence_level(confidence),
                risk_level=overall_risk_level,
                policy_conflicts=self._extract_policy_conflicts(risk_factors, compliance_context),
                access_violations=self._extract_access_violations(violations, risk_factors),
                mitigation_strategies=mitigation_recommendations,
                compliance_score=compliance_score,
                security_score=security_score,
                data_governance_score=data_governance_score,
                metadata={
                    "analysis_date": datetime.utcnow(),
                    "timeframe_analyzed": timeframe,
                    "usage_records_analyzed": len(usage_records),
                    "sessions_analyzed": len(sessions),
                    "risk_factors": risk_factors,
                    "mitigation_recommendations": mitigation_recommendations,
                    "potential_violations": violations,
                    "compliance_context": compliance_context
                }
            )
            
        except Exception as e:
            logger.error(f"Error predicting compliance risks for user {user_id}: {e}")
            raise
    
    def _parse_timeframe(self, timeframe: str) -> tuple:
        """Parse timeframe string to start and end dates"""
        now = datetime.utcnow()
        
        if timeframe.endswith('d'):
            days = int(timeframe[:-1])
            start_date = now - timedelta(days=days)
        elif timeframe.endswith('h'):
            hours = int(timeframe[:-1])
            start_date = now - timedelta(hours=hours)
        elif timeframe.endswith('w'):
            weeks = int(timeframe[:-1])
            start_date = now - timedelta(weeks=weeks)
        else:
            # Default to 30 days
            start_date = now - timedelta(days=30)
        
        return start_date, now
    
    async def _analyze_risk_factors(
        self, 
        usage_records: List[Dict[str, Any]], 
        sessions: List[Dict[str, Any]],
        compliance_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze risk factors from usage patterns"""
        risk_factors = {
            "data_access_risks": [],
            "security_risks": [],
            "compliance_risks": [],
            "behavioral_risks": [],
            "temporal_risks": []
        }
        
        if not usage_records:
            return risk_factors
        
        # Analyze data access patterns
        risk_factors["data_access_risks"] = self._analyze_data_access_risks(usage_records)
        
        # Analyze security patterns
        risk_factors["security_risks"] = self._analyze_security_risks(
            usage_records, sessions
        )
        
        # Analyze compliance indicators
        risk_factors["compliance_risks"] = self._analyze_compliance_risks(
            usage_records, compliance_context
        )
        
        # Analyze behavioral anomalies
        risk_factors["behavioral_risks"] = self._analyze_behavioral_risks(
            usage_records, sessions
        )
        
        # Analyze temporal patterns for risk
        risk_factors["temporal_risks"] = self._analyze_temporal_risks(usage_records)
        
        return risk_factors
    
    def _analyze_data_access_risks(self, usage_records: List[Dict[str, Any]]) -> List[str]:
        """Analyze data access patterns for risks"""
        risks = []
        
        # Check for high-risk data operations
        data_indicators = self.risk_indicators["data_access"]
        high_risk_operations = 0
        
        for record in usage_records:
            endpoint = record.get('endpoint', '').lower()
            tool_name = record.get('tool_name', '').lower()
            
            searchable_text = f"{endpoint} {tool_name}"
            
            # Check for high-risk keywords
            if any(keyword in searchable_text for keyword in data_indicators["high_risk"]):
                high_risk_operations += 1
            
            # Check for bulk operations
            tokens_used = record.get('tokens_used', 0)
            if tokens_used > 5000:  # Large token usage may indicate bulk operations
                risks.append("Large data processing operation detected")
        
        if high_risk_operations > len(usage_records) * 0.1:  # >10% high-risk operations
            risks.append("High frequency of sensitive data access operations")
        
        # Check for unusual data export patterns
        export_operations = [
            r for r in usage_records 
            if 'export' in r.get('endpoint', '').lower() or 'download' in r.get('endpoint', '').lower()
        ]
        
        if len(export_operations) > 5:
            risks.append("Multiple data export operations detected")
        
        return risks
    
    def _analyze_security_risks(
        self, 
        usage_records: List[Dict[str, Any]], 
        sessions: List[Dict[str, Any]]
    ) -> List[str]:
        """Analyze security-related risk patterns"""
        risks = []
        
        security_indicators = self.risk_indicators["security"]
        
        # Check for authentication-related activities
        auth_related = 0
        for record in usage_records:
            searchable_text = f"{record.get('endpoint', '')} {record.get('tool_name', '')}".lower()
            
            if any(keyword in searchable_text for keyword in security_indicators["keywords"]):
                auth_related += 1
        
        if auth_related > len(usage_records) * 0.2:  # >20% auth-related
            risks.append("High frequency of security/authentication related operations")
        
        # Analyze session patterns for security risks
        if sessions:
            # Check for unusually long sessions
            long_sessions = [
                s for s in sessions 
                if s.get('total_tokens', 0) > 10000
            ]
            
            if len(long_sessions) > len(sessions) * 0.3:
                risks.append("Unusually long sessions detected")
            
            # Check for rapid session creation
            session_times = []
            for session in sessions:
                created_at = session.get('created_at')
                if created_at:
                    try:
                        if isinstance(created_at, str):
                            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        else:
                            dt = created_at
                        session_times.append(dt)
                    except:
                        continue
            
            if len(session_times) >= 2:
                session_times.sort()
                quick_sessions = 0
                for i in range(1, len(session_times)):
                    if (session_times[i] - session_times[i-1]).total_seconds() < 300:  # 5 minutes
                        quick_sessions += 1
                
                if quick_sessions > len(session_times) * 0.3:
                    risks.append("Rapid session creation pattern detected")
        
        return risks
    
    def _analyze_compliance_risks(
        self, 
        usage_records: List[Dict[str, Any]], 
        compliance_context: Dict[str, Any]
    ) -> List[str]:
        """Analyze compliance-specific risks"""
        risks = []
        
        # Check for regulated data handling
        regulated_keywords = ["pii", "personal", "sensitive", "confidential", "gdpr", "hipaa"]
        regulated_operations = 0
        
        for record in usage_records:
            searchable_text = f"{record.get('endpoint', '')} {record.get('tool_name', '')}".lower()
            
            if any(keyword in searchable_text for keyword in regulated_keywords):
                regulated_operations += 1
        
        if regulated_operations > 0:
            ratio = regulated_operations / len(usage_records)
            if ratio > 0.1:  # >10% regulated data operations
                risks.append("High frequency of regulated data operations")
        
        # Check against compliance context requirements
        required_frameworks = compliance_context.get('required_frameworks', [])
        
        for framework in required_frameworks:
            if framework in self.compliance_frameworks:
                framework_info = self.compliance_frameworks[framework]
                critical_areas = framework_info['critical_areas']
                
                # Check if user operations align with critical areas
                area_violations = self._check_framework_compliance(usage_records, critical_areas)
                if area_violations:
                    risks.extend([f"{framework.upper()} compliance concern: {v}" for v in area_violations])
        
        return risks
    
    def _check_framework_compliance(
        self, 
        usage_records: List[Dict[str, Any]], 
        critical_areas: List[str]
    ) -> List[str]:
        """Check compliance with specific framework areas"""
        violations = []
        
        for area in critical_areas:
            area_keywords = {
                "data_processing": ["process", "transform", "analyze", "compute"],
                "consent": ["consent", "permission", "authorize", "approve"],
                "privacy": ["privacy", "personal", "private", "confidential"],
                "healthcare_data": ["health", "medical", "patient", "clinical"],
                "patient_info": ["patient", "medical_record", "health_data"],
                "financial_data": ["financial", "payment", "transaction", "money"],
                "audit_trail": ["audit", "log", "track", "monitor"],
                "security": ["security", "encrypt", "secure", "protect"],
                "risk_management": ["risk", "threat", "vulnerability", "assess"],
                "payment_data": ["payment", "card", "credit", "transaction"],
                "card_info": ["card", "credit_card", "payment_card"]
            }
            
            keywords = area_keywords.get(area, [])
            if not keywords:
                continue
            
            relevant_operations = 0
            for record in usage_records:
                searchable_text = f"{record.get('endpoint', '')} {record.get('tool_name', '')}".lower()
                
                if any(keyword in searchable_text for keyword in keywords):
                    relevant_operations += 1
            
            # Check for potential violations (heuristic-based)
            if relevant_operations > 10 and area in ["privacy", "patient_info", "financial_data"]:
                violations.append(f"High volume of {area.replace('_', ' ')} operations")
        
        return violations
    
    def _analyze_behavioral_risks(
        self, 
        usage_records: List[Dict[str, Any]], 
        sessions: List[Dict[str, Any]]
    ) -> List[str]:
        """Analyze behavioral patterns for risks"""
        risks = []
        
        if not usage_records:
            return risks
        
        # Check for usage pattern anomalies
        
        # 1. Unusual timing patterns
        hourly_usage = defaultdict(int)
        for record in usage_records:
            created_at = record.get('created_at')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        dt = created_at
                    hourly_usage[dt.hour] += 1
                except:
                    continue
        
        # Check for after-hours activity (outside 8 AM - 6 PM)
        after_hours = sum(count for hour, count in hourly_usage.items() if hour < 8 or hour > 18)
        total_usage = sum(hourly_usage.values())
        
        if total_usage > 0 and after_hours / total_usage > 0.3:  # >30% after hours
            risks.append("High after-hours activity detected")
        
        # 2. Usage volume anomalies
        daily_usage = defaultdict(int)
        for record in usage_records:
            created_at = record.get('created_at')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        dt = created_at
                    daily_usage[dt.date()] += 1
                except:
                    continue
        
        if len(daily_usage) > 1:
            usage_values = list(daily_usage.values())
            avg_daily = statistics.mean(usage_values)
            max_daily = max(usage_values)
            
            if max_daily > avg_daily * 3:  # Day with 3x average usage
                risks.append("Unusual usage volume spike detected")
        
        # 3. Tool usage anomalies
        tool_usage = Counter(record.get('tool_name', 'unknown') for record in usage_records)
        
        # Check for over-concentration on single tool
        if tool_usage:
            most_used_tool, most_used_count = tool_usage.most_common(1)[0]
            if most_used_count > len(usage_records) * 0.8:  # >80% usage of single tool
                risks.append(f"Over-concentration on single tool: {most_used_tool}")
        
        return risks
    
    def _analyze_temporal_risks(self, usage_records: List[Dict[str, Any]]) -> List[str]:
        """Analyze temporal patterns for risk indicators"""
        risks = []
        
        if not usage_records:
            return risks
        
        # Check for rapid-fire operations
        timestamps = []
        for record in usage_records:
            created_at = record.get('created_at')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        dt = created_at
                    timestamps.append(dt)
                except:
                    continue
        
        if len(timestamps) >= 2:
            timestamps.sort()
            rapid_operations = 0
            
            for i in range(1, len(timestamps)):
                if (timestamps[i] - timestamps[i-1]).total_seconds() < 10:  # Less than 10 seconds apart
                    rapid_operations += 1
            
            if rapid_operations > len(timestamps) * 0.2:  # >20% rapid operations
                risks.append("High frequency of rapid operations detected")
        
        # Check for weekend/holiday usage
        weekend_usage = 0
        for record in usage_records:
            created_at = record.get('created_at')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        dt = created_at
                    
                    if dt.weekday() >= 5:  # Saturday (5) or Sunday (6)
                        weekend_usage += 1
                except:
                    continue
        
        if len(usage_records) > 0 and weekend_usage / len(usage_records) > 0.2:  # >20% weekend
            risks.append("Significant weekend usage detected")
        
        return risks
    
    async def _calculate_compliance_score(
        self, 
        usage_records: List[Dict[str, Any]], 
        sessions: List[Dict[str, Any]],
        compliance_context: Dict[str, Any],
        risk_factors: Dict[str, Any]
    ) -> float:
        """Calculate compliance score (0-1, higher is better)"""
        base_score = 0.8  # Start with good compliance assumption
        
        # Deduct points for risk factors
        compliance_risks = risk_factors.get('compliance_risks', [])
        score_deduction = len(compliance_risks) * 0.1  # -0.1 per risk
        
        # Deduct for data access risks
        data_risks = risk_factors.get('data_access_risks', [])
        score_deduction += len(data_risks) * 0.05  # -0.05 per data risk
        
        # Bonus for compliance-positive behaviors
        if usage_records:
            # Check for audit-friendly behavior (consistent patterns)
            daily_usage = defaultdict(int)
            for record in usage_records:
                created_at = record.get('created_at')
                if created_at:
                    try:
                        if isinstance(created_at, str):
                            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        else:
                            dt = created_at
                        daily_usage[dt.date()] += 1
                    except:
                        continue
            
            if len(daily_usage) > 1:
                usage_values = list(daily_usage.values())
                if len(usage_values) > 1:
                    cv = statistics.stdev(usage_values) / statistics.mean(usage_values)
                    if cv < 0.5:  # Consistent usage pattern
                        base_score += 0.05
        
        final_score = max(0.0, min(1.0, base_score - score_deduction))
        return final_score
    
    async def _calculate_security_score(
        self, 
        usage_records: List[Dict[str, Any]], 
        sessions: List[Dict[str, Any]],
        user_profile: Optional[Dict[str, Any]],
        risk_factors: Dict[str, Any]
    ) -> float:
        """Calculate security score (0-1, higher is better)"""
        base_score = 0.75  # Start with decent security assumption
        
        # Deduct for security risks
        security_risks = risk_factors.get('security_risks', [])
        score_deduction = len(security_risks) * 0.1  # -0.1 per risk
        
        # Deduct for behavioral risks
        behavioral_risks = risk_factors.get('behavioral_risks', [])
        score_deduction += len(behavioral_risks) * 0.05  # -0.05 per behavioral risk
        
        # Bonus for security-positive behaviors
        if sessions:
            # Check for reasonable session durations
            long_sessions = [s for s in sessions if s.get('total_tokens', 0) > 20000]
            if len(long_sessions) < len(sessions) * 0.2:  # <20% very long sessions
                base_score += 0.05
        
        # User profile factors
        if user_profile:
            # Check subscription level (higher tiers may have better security practices)
            subscription = user_profile.get('subscription_status', 'free')
            if subscription in ['pro', 'enterprise']:
                base_score += 0.05
        
        final_score = max(0.0, min(1.0, base_score - score_deduction))
        return final_score
    
    async def _calculate_data_governance_score(
        self, 
        usage_records: List[Dict[str, Any]], 
        compliance_context: Dict[str, Any],
        risk_factors: Dict[str, Any]
    ) -> float:
        """Calculate data governance score (0-1, higher is better)"""
        base_score = 0.7  # Start with moderate governance assumption
        
        # Deduct for data access risks
        data_risks = risk_factors.get('data_access_risks', [])
        score_deduction = len(data_risks) * 0.1  # -0.1 per data risk
        
        # Deduct for temporal risks (unusual access patterns)
        temporal_risks = risk_factors.get('temporal_risks', [])
        score_deduction += len(temporal_risks) * 0.05  # -0.05 per temporal risk
        
        # Bonus for governance-positive behaviors
        if usage_records:
            # Check for moderate, consistent usage (good governance indicator)
            total_tokens = sum(record.get('tokens_used', 0) for record in usage_records)
            avg_tokens_per_operation = total_tokens / len(usage_records)
            
            if 50 <= avg_tokens_per_operation <= 500:  # Reasonable token usage
                base_score += 0.05
            
            # Check for proper tool usage diversity (not over-relying on single tool)
            tool_usage = Counter(record.get('tool_name', 'unknown') for record in usage_records)
            if len(tool_usage) >= 2:  # Using multiple tools appropriately
                base_score += 0.05
        
        # Context-based adjustments
        if compliance_context.get('data_classification') == 'sensitive':
            # Higher standards for sensitive data
            score_deduction += 0.1
        
        final_score = max(0.0, min(1.0, base_score - score_deduction))
        return final_score
    
    def _determine_risk_level(
        self, 
        compliance_score: float, 
        security_score: float, 
        data_governance_score: float
    ) -> str:
        """Determine overall risk level based on scores"""
        # Calculate weighted average (compliance weighted most heavily)
        overall_score = (
            compliance_score * 0.4 +
            security_score * 0.35 +
            data_governance_score * 0.25
        )
        
        if overall_score >= 0.8:
            return "low"
        elif overall_score >= 0.6:
            return "medium"
        else:
            return "high"
    
    async def _generate_mitigation_recommendations(
        self, 
        risk_factors: Dict[str, Any],
        compliance_score: float,
        security_score: float,
        data_governance_score: float
    ) -> List[str]:
        """Generate specific mitigation recommendations"""
        recommendations = []
        
        # Compliance-based recommendations
        if compliance_score < 0.6:
            recommendations.append("Implement comprehensive compliance training program")
            recommendations.append("Establish regular compliance audits and monitoring")
        
        compliance_risks = risk_factors.get('compliance_risks', [])
        if compliance_risks:
            recommendations.append("Address identified compliance violations immediately")
        
        # Security-based recommendations  
        if security_score < 0.6:
            recommendations.append("Strengthen access controls and authentication")
            recommendations.append("Implement security awareness training")
        
        security_risks = risk_factors.get('security_risks', [])
        if any("session" in risk.lower() for risk in security_risks):
            recommendations.append("Review and optimize session management policies")
        
        # Data governance recommendations
        if data_governance_score < 0.6:
            recommendations.append("Implement data classification and handling procedures")
            recommendations.append("Establish data access monitoring and controls")
        
        data_risks = risk_factors.get('data_access_risks', [])
        if data_risks:
            recommendations.append("Review and restrict sensitive data access permissions")
        
        # Behavioral risk recommendations
        behavioral_risks = risk_factors.get('behavioral_risks', [])
        if any("after-hours" in risk.lower() for risk in behavioral_risks):
            recommendations.append("Implement after-hours access controls and monitoring")
        
        temporal_risks = risk_factors.get('temporal_risks', [])
        if temporal_risks:
            recommendations.append("Implement rate limiting and usage pattern monitoring")
        
        return recommendations[:8]  # Limit to top 8 recommendations
    
    def _identify_potential_violations(
        self, 
        usage_records: List[Dict[str, Any]], 
        sessions: List[Dict[str, Any]],
        compliance_context: Dict[str, Any]
    ) -> List[str]:
        """Identify potential compliance violations"""
        violations = []
        
        # Check for potential data export violations
        export_operations = [
            r for r in usage_records 
            if 'export' in r.get('endpoint', '').lower() or 'download' in r.get('endpoint', '').lower()
        ]
        
        if len(export_operations) > 10:
            violations.append("Excessive data export operations - potential data exfiltration risk")
        
        # Check for after-hours access to sensitive operations
        sensitive_keywords = ["admin", "delete", "modify", "privileged", "sensitive"]
        after_hours_sensitive = 0
        
        for record in usage_records:
            created_at = record.get('created_at')
            endpoint = record.get('endpoint', '').lower()
            
            if created_at and any(keyword in endpoint for keyword in sensitive_keywords):
                try:
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        dt = created_at
                    
                    if dt.hour < 8 or dt.hour > 18:  # Outside business hours
                        after_hours_sensitive += 1
                except:
                    continue
        
        if after_hours_sensitive > 0:
            violations.append(f"After-hours access to sensitive operations: {after_hours_sensitive} instances")
        
        # Check for rapid bulk operations (potential automated misuse)
        bulk_operations = [r for r in usage_records if r.get('tokens_used', 0) > 5000]
        if len(bulk_operations) > 5:
            violations.append("Multiple bulk operations detected - review for compliance")
        
        return violations
    
    def _calculate_confidence(
        self, 
        usage_records: List[Dict[str, Any]], 
        sessions: List[Dict[str, Any]],
        compliance_context: Dict[str, Any],
        timeframe: str
    ) -> float:
        """Calculate confidence score for risk prediction"""
        confidence_factors = []
        
        # Data volume factor
        record_count = len(usage_records)
        if record_count >= 100:
            confidence_factors.append(0.9)
        elif record_count >= 50:
            confidence_factors.append(0.7)
        elif record_count >= 20:
            confidence_factors.append(0.5)
        else:
            confidence_factors.append(0.3)
        
        # Time coverage factor
        expected_days = 30 if timeframe == "30d" else 7 if timeframe == "7d" else 14
        time_span_days = self._calculate_time_span_days(usage_records)
        coverage = min(1.0, time_span_days / expected_days)
        confidence_factors.append(coverage)
        
        # Data quality factor
        complete_records = len([r for r in usage_records if r.get('endpoint') and r.get('created_at')])
        data_quality = complete_records / len(usage_records) if usage_records else 0
        confidence_factors.append(data_quality)
        
        # Context completeness factor
        context_completeness = len(compliance_context) / 5.0  # Expect ~5 context fields
        confidence_factors.append(min(1.0, context_completeness))
        
        # Calculate weighted average
        weights = [0.3, 0.25, 0.25, 0.2]
        weighted_confidence = sum(f * w for f, w in zip(confidence_factors, weights))
        
        return max(0.1, min(0.95, weighted_confidence))
    
    def _calculate_time_span_days(self, usage_records: List[Dict[str, Any]]) -> float:
        """Calculate time span of usage records in days"""
        if not usage_records:
            return 0.0
        
        timestamps = []
        for record in usage_records:
            created_at = record.get('created_at')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        dt = created_at
                    timestamps.append(dt)
                except:
                    continue
        
        if len(timestamps) < 2:
            return 1.0
        
        time_span = (max(timestamps) - min(timestamps)).total_seconds() / (24 * 3600)
        return max(1.0, time_span)
    
    def _extract_policy_conflicts(self, risk_factors: Dict[str, Any], compliance_context: Dict[str, Any]) -> List[str]:
        """Extract policy conflicts from risk analysis"""
        conflicts = []
        
        # Check compliance risk factors for policy conflicts
        compliance_risks = risk_factors.get('compliance_risks', [])
        for risk in compliance_risks:
            if 'policy' in risk.lower() or 'violation' in risk.lower():
                conflicts.append(risk)
        
        # Check access patterns against policies
        data_access_risks = risk_factors.get('data_access_risks', [])
        for risk in data_access_risks:
            if 'unauthorized' in risk.lower() or 'excessive' in risk.lower():
                conflicts.append(f"Access policy conflict: {risk}")
        
        # Check role-based conflicts
        user_role = compliance_context.get('user_role', '')
        access_level = compliance_context.get('access_level', '')
        if user_role == 'user' and access_level == 'admin':
            conflicts.append("Role-permission mismatch: User role with admin access")
        
        return conflicts
    
    def _extract_access_violations(self, violations: List[Dict[str, Any]], risk_factors: Dict[str, Any]) -> List[str]:
        """Extract access violations from analysis"""
        access_violations = []
        
        # Extract from identified violations
        for violation in violations:
            if violation.get('type') in ['access', 'permission', 'authorization']:
                access_violations.append(violation.get('description', str(violation)))
        
        # Extract from behavioral risks
        behavioral_risks = risk_factors.get('behavioral_risks', [])
        for risk in behavioral_risks:
            if 'access' in risk.lower() or 'permission' in risk.lower():
                access_violations.append(f"Behavioral violation: {risk}")
        
        # Extract from security risks related to access
        security_risks = risk_factors.get('security_risks', [])
        for risk in security_risks:
            if 'access' in risk.lower() or 'unauthorized' in risk.lower():
                access_violations.append(f"Security violation: {risk}")
        
        return access_violations

    def _determine_confidence_level(self, confidence: float) -> PredictionConfidenceLevel:
        """Determine confidence level category"""
        if confidence >= 0.8:
            return PredictionConfidenceLevel.VERY_HIGH
        elif confidence >= 0.6:
            return PredictionConfidenceLevel.HIGH
        elif confidence >= 0.4:
            return PredictionConfidenceLevel.MEDIUM
        else:
            return PredictionConfidenceLevel.LOW
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for compliance risk predictor"""
        try:
            health_status = "healthy"
            details = {}
            
            # Test repository connections
            try:
                await self.usage_repository.get_user_usage_history("health_check", limit=1)
                details["usage_repository"] = "healthy"
            except Exception as e:
                details["usage_repository"] = f"unhealthy: {str(e)}"
                health_status = "degraded"
            
            try:
                await self.session_repository.get_user_sessions("health_check", limit=1)
                details["session_repository"] = "healthy"
            except Exception as e:
                details["session_repository"] = f"unhealthy: {str(e)}"
                health_status = "degraded"
            
            return {
                "status": health_status,
                "component": "compliance_risk_predictor",
                "details": details,
                "last_check": datetime.utcnow()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "component": "compliance_risk_predictor",
                "error": str(e),
                "last_check": datetime.utcnow()
            }