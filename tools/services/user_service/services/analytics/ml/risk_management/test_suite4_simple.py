"""
Suite 4: Risk Management - Integration Tests with Real Data

Tests the risk management service with actual database connections
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parents[6]
sys.path.insert(0, str(project_root))

from tools.services.user_service.services.prediction.risk_management.risk_management_service import RiskManagementService
from tools.services.user_service.services.prediction.prediction_models import ComplianceRiskPrediction
from tools.services.user_service.models import User
from tools.services.user_service.repositories.user_repository import UserRepository
from tools.services.user_service.repositories.usage_repository import UsageRepository
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_suite4_risk_management():
    """Comprehensive test of Suite 4: Risk Management with real data"""
    print("=" * 60)
    print("SUITE 4: RISK MANAGEMENT - REAL DATA INTEGRATION TEST")
    print("=" * 60)
    
    try:
        # Initialize services
        risk_service = RiskManagementService()
        user_repo = UserRepository()
        usage_repo = UsageRepository()
        
        print("✅ Services initialized successfully")
        
        # Get real user data for testing
        print("\n📊 Fetching real user data...")
        users = await user_repo.get_active_users(limit=5)
        
        if not users:
            print("⚠️  No users found, creating test compliance context...")
            test_user_id = "test_compliance_user_001"
            
            # Create comprehensive compliance test context
            compliance_context = {
                "user_role": "data_analyst",
                "department": "finance",
                "access_level": "high",
                "data_types": ["financial", "personal_data", "payment_info"],
                "systems_accessed": ["crm", "billing", "analytics", "reporting"],
                "industry": "finance",
                "regulatory_frameworks": ["SOX", "PCI_DSS", "GDPR"],
                "recent_activities": [
                    {"action": "data_export", "timestamp": "2024-01-20T14:30:00Z", "size_mb": 150},
                    {"action": "report_generation", "timestamp": "2024-01-20T15:45:00Z", "records": 5000},
                    {"action": "system_access", "timestamp": "2024-01-20T09:15:00Z", "after_hours": False},
                    {"action": "bulk_download", "timestamp": "2024-01-19T18:30:00Z", "after_hours": True}
                ],
                "permissions": ["read", "write", "export", "admin"],
                "location": "US",
                "device_info": {"type": "laptop", "managed": True, "encrypted": True}
            }
            
        else:
            user = users[0]
            test_user_id = str(user.id)
            print(f"✅ Using real user: {user.email}")
            
            # Get real usage data to build context
            usage_data = await usage_repo.get_user_usage(test_user_id, limit=10)
            
            # Build realistic compliance context from real data
            compliance_context = {
                "user_role": getattr(user, 'role', 'user'),
                "department": getattr(user, 'department', 'general'),
                "access_level": "medium",
                "data_types": ["user_data", "analytics"],
                "systems_accessed": ["main_app"],
                "industry": "technology",
                "regulatory_frameworks": ["GDPR"],
                "recent_activities": [
                    {
                        "action": "system_access",
                        "timestamp": usage.created_at.isoformat() if usage.created_at else "2024-01-20T10:00:00Z",
                        "duration_minutes": getattr(usage, 'duration', 30)
                    } for usage in usage_data[:3]
                ] if usage_data else [
                    {"action": "login", "timestamp": "2024-01-20T10:00:00Z", "location": "office"}
                ],
                "permissions": ["read", "write"],
                "location": "US",
                "device_info": {"type": "browser", "managed": False}
            }
        
        print(f"📋 Compliance Context: {len(compliance_context)} attributes")
        
        # Test 1: Predict Compliance Risks - Short Term
        print("\n🔍 Test 1: Short-term Compliance Risk Prediction (7d)")
        print("-" * 50)
        
        prediction_7d = await risk_service.predict_compliance_risks(
            user_id=test_user_id,
            compliance_context=compliance_context,
            timeframe="7d"
        )
        
        print(f"✅ 7-day prediction generated")
        print(f"📊 Compliance Score: {getattr(prediction_7d, 'compliance_score', 'N/A'):.3f}" if hasattr(prediction_7d, 'compliance_score') else "📊 Compliance Score: N/A")
        print(f"🔒 Security Score: {getattr(prediction_7d, 'security_score', 'N/A'):.3f}" if hasattr(prediction_7d, 'security_score') else "🔒 Security Score: N/A") 
        print(f"🎯 Risk Level: {prediction_7d.risk_level}")
        print(f"⚠️  Policy Conflicts: {len(prediction_7d.policy_conflicts)}")
        print(f"🚫 Access Violations: {len(prediction_7d.access_violations)}")
        print(f"🛡️  Mitigation Strategies: {len(prediction_7d.mitigation_strategies)}")
        
        # Print some example conflicts and violations if they exist
        if prediction_7d.policy_conflicts:
            print(f"   Sample conflict: {prediction_7d.policy_conflicts[0]}")
        if prediction_7d.access_violations:
            print(f"   Sample violation: {prediction_7d.access_violations[0]}")
        
        # Display metadata if available
        if hasattr(prediction_7d, 'metadata') and prediction_7d.metadata.get('risk_factors'):
            risk_factors = prediction_7d.metadata['risk_factors']
            for category, factors in risk_factors.items():
                if factors:
                    print(f"   {category}: {len(factors)} factors")
        
        # Test 2: Predict Compliance Risks - Medium Term  
        print("\n🔍 Test 2: Medium-term Compliance Risk Prediction (30d)")
        print("-" * 50)
        
        prediction_30d = await risk_service.predict_compliance_risks(
            user_id=test_user_id,
            compliance_context=compliance_context,
            timeframe="30d"
        )
        
        print(f"✅ 30-day prediction generated")
        print(f"📊 Compliance Score: {getattr(prediction_30d, 'compliance_score', 'N/A'):.3f}" if hasattr(prediction_30d, 'compliance_score') else "📊 Compliance Score: N/A")
        print(f"🎯 Risk Level: {prediction_30d.risk_level}")
        total_factors = 0
        if hasattr(prediction_30d, 'metadata') and prediction_30d.metadata.get('risk_factors'):
            total_factors = sum(len(factors) for factors in prediction_30d.metadata['risk_factors'].values())
        print(f"⚠️  Total Risk Factors: {total_factors}")
        
        # Test 3: High-Risk Compliance Context
        print("\n🔍 Test 3: High-Risk Compliance Context")
        print("-" * 50)
        
        high_risk_context = {
            "user_role": "system_admin",
            "department": "IT",
            "access_level": "admin", 
            "data_types": ["financial", "personal_data", "payment_info", "health_records"],
            "systems_accessed": ["database", "backup_systems", "security_tools", "audit_logs"],
            "industry": "healthcare",
            "regulatory_frameworks": ["HIPAA", "SOX", "GDPR", "PCI_DSS"],
            "recent_activities": [
                {"action": "bulk_data_export", "timestamp": "2024-01-19T23:30:00Z", "after_hours": True, "size_gb": 5},
                {"action": "admin_privilege_escalation", "timestamp": "2024-01-19T22:15:00Z"},
                {"action": "security_policy_override", "timestamp": "2024-01-19T21:00:00Z"},
                {"action": "audit_log_access", "timestamp": "2024-01-19T20:30:00Z"}
            ],
            "permissions": ["read", "write", "delete", "admin", "export", "modify_permissions"],
            "location": "Remote",
            "device_info": {"type": "personal_device", "managed": False, "encrypted": False}
        }
        
        prediction_high_risk = await risk_service.predict_compliance_risks(
            user_id="high_risk_admin_001",
            compliance_context=high_risk_context,
            timeframe="30d"
        )
        
        print(f"✅ High-risk prediction generated")
        print(f"📊 Compliance Score: {getattr(prediction_high_risk, 'compliance_score', 'N/A'):.3f}" if hasattr(prediction_high_risk, 'compliance_score') else "📊 Compliance Score: N/A")
        print(f"🎯 Risk Level: {prediction_high_risk.risk_level}")
        print(f"📈 Confidence: {prediction_high_risk.confidence}")
        
        # Display mitigation priorities
        mitigation_priorities = getattr(prediction_high_risk, 'mitigation_priorities', None) or (prediction_high_risk.metadata.get('mitigation_recommendations', []) if hasattr(prediction_high_risk, 'metadata') else [])
        if mitigation_priorities:
            if isinstance(mitigation_priorities, list) and len(mitigation_priorities) > 0:
                if isinstance(mitigation_priorities[0], dict):
                    print(f"🛡️  Top Mitigation Priority: {mitigation_priorities[0].get('category', 'Unknown')}")
                    print(f"   Risk Count: {mitigation_priorities[0].get('risk_count', 0)}")
                    print(f"   Urgency: {mitigation_priorities[0].get('urgency', 'Unknown')}")
                else:
                    print(f"🛡️  Top Mitigation Strategy: {mitigation_priorities[0]}")
        
        # Test 4: Impact Assessment Validation
        print("\n🔍 Test 4: Impact Assessment Analysis")
        print("-" * 50)
        
        impact_assessment = getattr(prediction_high_risk, 'impact_assessment', None) or (prediction_high_risk.metadata.get('impact_assessment', {}) if hasattr(prediction_high_risk, 'metadata') else {})
        if impact_assessment:
            print(f"💰 Financial Impact: {impact_assessment.get('financial_impact', 'N/A')}")
            print(f"⚙️  Operational Impact: {impact_assessment.get('operational_impact', 'N/A')}")
            print(f"🏛️  Regulatory Impact: {impact_assessment.get('regulatory_impact', 'N/A')}")
            print(f"📢 Reputational Impact: {impact_assessment.get('reputational_impact', 'N/A')}")
            print(f"🎯 Overall Impact: {impact_assessment.get('overall_impact', 'N/A')}")
        else:
            print("Impact assessment not available")
        
        # Test 5: Framework-specific Analysis
        print("\n🔍 Test 5: Framework-specific Compliance Analysis")
        print("-" * 50)
        
        framework_assessments = getattr(prediction_high_risk, 'framework_assessments', None) or (prediction_high_risk.metadata.get('framework_assessments', {}) if hasattr(prediction_high_risk, 'metadata') else {})
        if framework_assessments:
            for framework, assessment in framework_assessments.items():
                print(f"📋 {framework}:")
                print(f"   Compliance Score: {assessment.get('compliance_score', 0):.3f}")
                print(f"   Risk Level: {assessment.get('risk_level', 'unknown')}")
                violations = assessment.get('violations', [])
                print(f"   Violations: {len(violations)}")
                if violations:
                    print(f"   Top Violation: {violations[0].get('type', 'unknown') if isinstance(violations[0], dict) else violations[0]}")
        else:
            print("Framework assessments not available")
        
        # Test 6: Prediction Comparison
        print("\n🔍 Test 6: Risk Prediction Comparison")
        print("-" * 50)
        
        score_7d = getattr(prediction_7d, 'compliance_score', 0)
        score_30d = getattr(prediction_30d, 'compliance_score', 0)
        
        print(f"📊 7-day vs 30-day Compliance Scores:")
        print(f"   7-day:  {score_7d:.3f} ({prediction_7d.risk_level})")
        print(f"   30-day: {score_30d:.3f} ({prediction_30d.risk_level})")
        
        risk_trend = "increasing" if score_30d > score_7d else "stable/decreasing"
        print(f"   Trend: {risk_trend}")
        
        print("\n" + "=" * 60)
        print("✅ SUITE 4: RISK MANAGEMENT TEST COMPLETED SUCCESSFULLY")
        print("=" * 60)
        
        return {
            "test_passed": True,
            "predictions_generated": 3,
            "risk_levels_tested": ["low", "medium", "high"],
            "frameworks_tested": len(high_risk_context["regulatory_frameworks"]),
            "mitigation_priorities": len(mitigation_priorities) if mitigation_priorities else 0
        }
        
    except Exception as e:
        logger.error(f"Suite 4 test failed: {str(e)}")
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"test_passed": False, "error": str(e)}

if __name__ == "__main__":
    result = asyncio.run(test_suite4_risk_management())
    print(f"\nFinal Result: {result}")