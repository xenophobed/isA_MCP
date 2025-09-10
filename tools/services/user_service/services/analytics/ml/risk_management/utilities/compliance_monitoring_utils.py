"""
Compliance Monitoring Utilities

Utilities for monitoring and analyzing compliance with various frameworks
"""

from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re


class ComplianceMonitoringUtils:
    """Utilities for compliance monitoring and framework analysis"""
    
    # Compliance frameworks and their requirements
    COMPLIANCE_FRAMEWORKS = {
        "gdpr": {
            "name": "General Data Protection Regulation",
            "critical_requirements": [
                "data_minimization",
                "purpose_limitation", 
                "consent_management",
                "data_subject_rights",
                "breach_notification",
                "privacy_by_design"
            ],
            "risk_keywords": ["personal", "pii", "gdpr", "consent", "privacy"],
            "violation_patterns": ["bulk_export", "unauthorized_access", "retention_violation"]
        },
        "hipaa": {
            "name": "Health Insurance Portability and Accountability Act",
            "critical_requirements": [
                "safeguards_rule",
                "minimum_necessary",
                "access_controls",
                "audit_controls", 
                "integrity_controls",
                "transmission_security"
            ],
            "risk_keywords": ["health", "medical", "patient", "phi", "hipaa"],
            "violation_patterns": ["unauthorized_disclosure", "inadequate_safeguards"]
        },
        "sox": {
            "name": "Sarbanes-Oxley Act",
            "critical_requirements": [
                "financial_reporting_controls",
                "audit_trail_maintenance",
                "change_management",
                "segregation_of_duties",
                "documentation_requirements"
            ],
            "risk_keywords": ["financial", "audit", "sox", "controls", "reporting"],
            "violation_patterns": ["inadequate_controls", "audit_trail_gaps"]
        },
        "pci_dss": {
            "name": "Payment Card Industry Data Security Standard",
            "critical_requirements": [
                "secure_network",
                "protect_cardholder_data",
                "vulnerability_management",
                "access_control_measures",
                "network_monitoring",
                "information_security_policy"
            ],
            "risk_keywords": ["payment", "card", "credit", "transaction", "pci"],
            "violation_patterns": ["insecure_transmission", "inadequate_encryption"]
        },
        "iso27001": {
            "name": "ISO/IEC 27001 Information Security Management",
            "critical_requirements": [
                "information_security_policy",
                "risk_management",
                "asset_management",
                "access_control",
                "incident_management",
                "business_continuity"
            ],
            "risk_keywords": ["security", "iso", "isms", "controls", "risk"],
            "violation_patterns": ["security_policy_violation", "inadequate_controls"]
        }
    }
    
    @staticmethod
    def assess_framework_compliance(
        usage_records: List[Dict[str, Any]],
        framework: str,
        compliance_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Assess compliance with a specific framework
        
        Args:
            usage_records: User activity records
            framework: Framework name (gdpr, hipaa, etc.)
            compliance_context: Context information for compliance assessment
            
        Returns:
            Framework compliance assessment
        """
        if framework not in ComplianceMonitoringUtils.COMPLIANCE_FRAMEWORKS:
            return {"error": f"Unknown framework: {framework}"}
        
        framework_info = ComplianceMonitoringUtils.COMPLIANCE_FRAMEWORKS[framework]
        
        # Analyze usage patterns against framework requirements
        compliance_score = ComplianceMonitoringUtils._calculate_framework_score(
            usage_records, framework_info, compliance_context
        )
        
        # Identify potential violations
        violations = ComplianceMonitoringUtils._identify_framework_violations(
            usage_records, framework_info
        )
        
        # Check critical requirements
        requirements_status = ComplianceMonitoringUtils._check_critical_requirements(
            usage_records, framework_info, compliance_context
        )
        
        # Generate recommendations
        recommendations = ComplianceMonitoringUtils._generate_framework_recommendations(
            framework, compliance_score, violations, requirements_status
        )
        
        return {
            "framework": framework,
            "framework_name": framework_info["name"],
            "compliance_score": compliance_score,
            "compliance_level": ComplianceMonitoringUtils._classify_compliance_level(compliance_score),
            "violations": violations,
            "requirements_status": requirements_status,
            "recommendations": recommendations,
            "assessment_timestamp": datetime.utcnow()
        }
    
    @staticmethod
    def _calculate_framework_score(
        usage_records: List[Dict[str, Any]],
        framework_info: Dict[str, Any],
        compliance_context: Dict[str, Any]
    ) -> float:
        """Calculate compliance score for a specific framework"""
        base_score = 0.8  # Start with good compliance assumption
        
        risk_keywords = framework_info["risk_keywords"]
        violation_patterns = framework_info["violation_patterns"]
        
        # Deduct points for risky activities
        risky_activities = 0
        total_activities = len(usage_records)
        
        for record in usage_records:
            endpoint = record.get('endpoint', '').lower()
            tool_name = record.get('tool_name', '').lower()
            searchable_text = f"{endpoint} {tool_name}"
            
            # Check for framework-specific risk keywords
            if any(keyword in searchable_text for keyword in risk_keywords):
                risky_activities += 1
        
        if total_activities > 0:
            risk_ratio = risky_activities / total_activities
            if risk_ratio > 0.3:  # >30% risky activities
                base_score -= 0.2
            elif risk_ratio > 0.1:  # >10% risky activities
                base_score -= 0.1
        
        # Check for violation patterns
        violation_count = ComplianceMonitoringUtils._count_violation_patterns(
            usage_records, violation_patterns
        )
        
        if violation_count > 0:
            base_score -= min(0.3, violation_count * 0.1)  # -0.1 per violation, max -0.3
        
        # Context-based adjustments
        data_sensitivity = compliance_context.get('data_sensitivity', 'normal')
        if data_sensitivity == 'high':
            base_score -= 0.05  # Higher standards for sensitive data
        
        return max(0.0, min(1.0, base_score))
    
    @staticmethod
    def _count_violation_patterns(
        usage_records: List[Dict[str, Any]],
        violation_patterns: List[str]
    ) -> int:
        """Count occurrences of violation patterns"""
        violations = 0
        
        pattern_keywords = {
            "bulk_export": ["export", "download", "bulk", "mass"],
            "unauthorized_access": ["admin", "root", "privilege", "escalate"],
            "retention_violation": ["old", "archive", "delete", "purge"],
            "unauthorized_disclosure": ["share", "send", "forward", "leak"],
            "inadequate_safeguards": ["unsecure", "unencrypted", "public"],
            "inadequate_controls": ["bypass", "override", "disable"],
            "audit_trail_gaps": ["log", "audit", "trace", "monitor"],
            "insecure_transmission": ["http", "unencrypted", "plain"],
            "inadequate_encryption": ["plain", "clear", "unencrypted"],
            "security_policy_violation": ["policy", "violation", "breach"]
        }
        
        for pattern in violation_patterns:
            pattern_keywords_list = pattern_keywords.get(pattern, [])
            
            for record in usage_records:
                searchable_text = f"{record.get('endpoint', '')} {record.get('tool_name', '')}".lower()
                
                if any(keyword in searchable_text for keyword in pattern_keywords_list):
                    # Additional checks for context
                    tokens_used = record.get('tokens_used', 0)
                    
                    if pattern == "bulk_export" and tokens_used > 5000:
                        violations += 1
                    elif pattern in ["unauthorized_access", "inadequate_controls"]:
                        violations += 1
                    elif pattern in ["retention_violation", "audit_trail_gaps"]:
                        violations += 1
        
        return violations
    
    @staticmethod
    def _identify_framework_violations(
        usage_records: List[Dict[str, Any]],
        framework_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify specific violations of framework requirements"""
        violations = []
        
        violation_patterns = framework_info["violation_patterns"]
        risk_keywords = framework_info["risk_keywords"]
        
        # Track violation instances
        for record in usage_records:
            endpoint = record.get('endpoint', '').lower()
            tool_name = record.get('tool_name', '').lower()
            created_at = record.get('created_at')
            tokens_used = record.get('tokens_used', 0)
            
            searchable_text = f"{endpoint} {tool_name}"
            
            # Check for specific violation patterns
            for pattern in violation_patterns:
                if ComplianceMonitoringUtils._matches_violation_pattern(
                    record, pattern
                ):
                    violations.append({
                        "type": pattern,
                        "description": f"Potential {pattern.replace('_', ' ')} detected",
                        "endpoint": endpoint,
                        "tool_name": tool_name,
                        "timestamp": created_at,
                        "severity": ComplianceMonitoringUtils._assess_violation_severity(
                            pattern, tokens_used
                        ),
                        "details": {
                            "tokens_used": tokens_used,
                            "searchable_content": searchable_text
                        }
                    })
        
        # Remove duplicates and sort by severity
        unique_violations = []
        seen_combinations = set()
        
        for violation in violations:
            key = (violation["type"], violation["endpoint"], violation.get("timestamp", ""))
            if key not in seen_combinations:
                unique_violations.append(violation)
                seen_combinations.add(key)
        
        # Sort by severity (high first)
        severity_order = {"high": 3, "medium": 2, "low": 1}
        unique_violations.sort(
            key=lambda x: severity_order.get(x["severity"], 0), 
            reverse=True
        )
        
        return unique_violations[:10]  # Limit to top 10 violations
    
    @staticmethod
    def _matches_violation_pattern(record: Dict[str, Any], pattern: str) -> bool:
        """Check if a record matches a specific violation pattern"""
        endpoint = record.get('endpoint', '').lower()
        tool_name = record.get('tool_name', '').lower()
        tokens_used = record.get('tokens_used', 0)
        
        searchable_text = f"{endpoint} {tool_name}"
        
        pattern_checks = {
            "bulk_export": (
                any(keyword in searchable_text for keyword in ["export", "download", "bulk"]) and
                tokens_used > 3000
            ),
            "unauthorized_access": (
                any(keyword in searchable_text for keyword in ["admin", "privilege", "root"])
            ),
            "retention_violation": (
                any(keyword in searchable_text for keyword in ["delete", "purge", "archive"]) and
                tokens_used > 1000
            ),
            "unauthorized_disclosure": (
                any(keyword in searchable_text for keyword in ["share", "send", "export"])
            ),
            "inadequate_safeguards": (
                any(keyword in searchable_text for keyword in ["unsecure", "public"])
            ),
            "inadequate_controls": (
                any(keyword in searchable_text for keyword in ["bypass", "override"])
            ),
            "audit_trail_gaps": (
                "audit" in searchable_text and tokens_used > 2000
            ),
            "insecure_transmission": (
                any(keyword in searchable_text for keyword in ["http", "unencrypted"])
            ),
            "inadequate_encryption": (
                any(keyword in searchable_text for keyword in ["plain", "clear"])
            ),
            "security_policy_violation": (
                any(keyword in searchable_text for keyword in ["policy", "violation"])
            )
        }
        
        return pattern_checks.get(pattern, False)
    
    @staticmethod
    def _assess_violation_severity(pattern: str, tokens_used: int) -> str:
        """Assess the severity of a violation"""
        high_severity_patterns = [
            "unauthorized_access", 
            "unauthorized_disclosure", 
            "inadequate_safeguards",
            "security_policy_violation"
        ]
        
        medium_severity_patterns = [
            "bulk_export", 
            "retention_violation", 
            "inadequate_controls",
            "insecure_transmission"
        ]
        
        if pattern in high_severity_patterns:
            return "high"
        elif pattern in medium_severity_patterns:
            return "medium"
        else:
            return "low"
        
        # Adjust based on token usage (higher usage = higher severity)
        if tokens_used > 10000:
            if severity == "low":
                return "medium"
            elif severity == "medium":
                return "high"
        
        return severity
    
    @staticmethod
    def _check_critical_requirements(
        usage_records: List[Dict[str, Any]],
        framework_info: Dict[str, Any],
        compliance_context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Check status of critical framework requirements"""
        requirements = framework_info["critical_requirements"]
        requirements_status = {}
        
        # This is a simplified check - in practice, would need more sophisticated analysis
        for requirement in requirements:
            # Default to "unknown" - would need more context to properly assess
            requirements_status[requirement] = ComplianceMonitoringUtils._assess_requirement_status(
                requirement, usage_records, compliance_context
            )
        
        return requirements_status
    
    @staticmethod
    def _assess_requirement_status(
        requirement: str,
        usage_records: List[Dict[str, Any]],
        compliance_context: Dict[str, Any]
    ) -> str:
        """Assess the status of a specific requirement"""
        # Simplified heuristic-based assessment
        # In practice, this would require more sophisticated analysis
        
        requirement_keywords = {
            "data_minimization": ["minimal", "necessary", "limited"],
            "purpose_limitation": ["purpose", "limited", "specific"],
            "consent_management": ["consent", "permission", "authorize"],
            "data_subject_rights": ["rights", "access", "delete", "portability"],
            "breach_notification": ["breach", "incident", "notify"],
            "privacy_by_design": ["privacy", "design", "default"],
            "safeguards_rule": ["safeguard", "protect", "secure"],
            "minimum_necessary": ["minimum", "necessary", "limited"],
            "access_controls": ["access", "control", "permission", "auth"],
            "audit_controls": ["audit", "log", "monitor", "track"],
            "integrity_controls": ["integrity", "validate", "verify"],
            "transmission_security": ["secure", "encrypt", "transmission"],
            "financial_reporting_controls": ["financial", "report", "control"],
            "audit_trail_maintenance": ["audit", "trail", "maintain", "log"],
            "change_management": ["change", "manage", "control", "approve"],
            "segregation_of_duties": ["segregate", "separate", "duties"],
            "documentation_requirements": ["document", "record", "maintain"],
            "secure_network": ["network", "secure", "firewall"],
            "protect_cardholder_data": ["cardholder", "protect", "data"],
            "vulnerability_management": ["vulnerability", "scan", "patch"],
            "access_control_measures": ["access", "control", "measure"],
            "network_monitoring": ["network", "monitor", "traffic"],
            "information_security_policy": ["security", "policy", "information"],
            "risk_management": ["risk", "assess", "manage"],
            "asset_management": ["asset", "inventory", "manage"],
            "incident_management": ["incident", "response", "manage"],
            "business_continuity": ["continuity", "backup", "recovery"]
        }
        
        keywords = requirement_keywords.get(requirement, [])
        if not keywords:
            return "unknown"
        
        # Check if there are activities related to this requirement
        related_activities = 0
        for record in usage_records:
            searchable_text = f"{record.get('endpoint', '')} {record.get('tool_name', '')}".lower()
            
            if any(keyword in searchable_text for keyword in keywords):
                related_activities += 1
        
        # Simple heuristic assessment
        if related_activities == 0:
            return "not_addressed"
        elif related_activities < 3:
            return "partially_addressed"
        else:
            return "addressed"
    
    @staticmethod
    def _classify_compliance_level(compliance_score: float) -> str:
        """Classify numerical compliance score into categorical level"""
        if compliance_score >= 0.9:
            return "excellent"
        elif compliance_score >= 0.8:
            return "good"
        elif compliance_score >= 0.6:
            return "acceptable"
        elif compliance_score >= 0.4:
            return "needs_improvement"
        else:
            return "poor"
    
    @staticmethod
    def _generate_framework_recommendations(
        framework: str,
        compliance_score: float,
        violations: List[Dict[str, Any]],
        requirements_status: Dict[str, str]
    ) -> List[str]:
        """Generate framework-specific recommendations"""
        recommendations = []
        
        # Score-based recommendations
        if compliance_score < 0.6:
            recommendations.append(f"Urgent: {framework.upper()} compliance score is below acceptable level")
            recommendations.append(f"Implement comprehensive {framework.upper()} compliance program")
        elif compliance_score < 0.8:
            recommendations.append(f"Enhance {framework.upper()} compliance measures")
        
        # Violation-based recommendations
        high_severity_violations = [v for v in violations if v.get("severity") == "high"]
        if high_severity_violations:
            recommendations.append("Address high-severity compliance violations immediately")
        
        if len(violations) > 5:
            recommendations.append("Implement automated compliance monitoring")
        
        # Requirements-based recommendations
        not_addressed = [req for req, status in requirements_status.items() if status == "not_addressed"]
        if not_addressed:
            recommendations.append(f"Address unmet requirements: {', '.join(not_addressed[:3])}")
        
        partially_addressed = [req for req, status in requirements_status.items() if status == "partially_addressed"]
        if partially_addressed:
            recommendations.append(f"Strengthen partially addressed requirements")
        
        # Framework-specific recommendations
        framework_specific = {
            "gdpr": [
                "Implement privacy impact assessments",
                "Establish data subject request procedures",
                "Ensure consent management systems"
            ],
            "hipaa": [
                "Conduct risk assessments for PHI handling",
                "Implement business associate agreements",
                "Establish incident response procedures"
            ],
            "sox": [
                "Strengthen internal financial controls",
                "Implement change management processes",
                "Maintain comprehensive audit trails"
            ],
            "pci_dss": [
                "Implement network segmentation",
                "Regular vulnerability scanning",
                "Maintain cardholder data inventory"
            ],
            "iso27001": [
                "Establish information security management system",
                "Implement risk treatment plans",
                "Conduct regular security assessments"
            ]
        }
        
        if framework in framework_specific:
            recommendations.extend(framework_specific[framework][:2])
        
        return recommendations[:8]  # Limit to top 8 recommendations
    
    @staticmethod
    def monitor_compliance_trends(
        historical_assessments: List[Dict[str, Any]],
        framework: str
    ) -> Dict[str, Any]:
        """Monitor compliance trends over time for a specific framework"""
        
        if len(historical_assessments) < 2:
            return {
                "trend": "insufficient_data",
                "framework": framework
            }
        
        # Sort by timestamp
        sorted_assessments = sorted(
            historical_assessments,
            key=lambda x: x.get('assessment_timestamp', datetime.min)
        )
        
        # Extract compliance scores over time
        scores = [assessment.get('compliance_score', 0.0) for assessment in sorted_assessments]
        
        # Calculate trend
        if len(scores) >= 2:
            recent_avg = sum(scores[-3:]) / min(3, len(scores))  # Last 3 assessments
            earlier_avg = sum(scores[:3]) / min(3, len(scores))  # First 3 assessments
            
            if recent_avg > earlier_avg + 0.05:
                trend = "improving"
            elif recent_avg < earlier_avg - 0.05:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        # Analyze violation trends
        violation_counts = [len(assessment.get('violations', [])) for assessment in sorted_assessments]
        avg_recent_violations = sum(violation_counts[-3:]) / min(3, len(violation_counts))
        avg_earlier_violations = sum(violation_counts[:3]) / min(3, len(violation_counts))
        
        violation_trend = "stable"
        if avg_recent_violations > avg_earlier_violations + 1:
            violation_trend = "increasing"
        elif avg_recent_violations < avg_earlier_violations - 1:
            violation_trend = "decreasing"
        
        return {
            "framework": framework,
            "compliance_trend": trend,
            "violation_trend": violation_trend,
            "current_score": scores[-1] if scores else 0.0,
            "score_change": scores[-1] - scores[0] if len(scores) >= 2 else 0.0,
            "assessments_analyzed": len(sorted_assessments)
        }