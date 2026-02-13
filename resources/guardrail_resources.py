#!/usr/bin/env python3
"""
Guardrail Resources for PII and Medical Information Security Compliance
"""

import json
import re
from typing import Dict, List, Any
from mcp.server.fastmcp import FastMCP
from core.logging import get_logger

logger = get_logger(__name__)


class GuardrailConfig:
    """Configuration for guardrail checks"""

    def __init__(self):
        self.pii_patterns = {
            "ssn": r"\b\d{3}-?\d{2}-?\d{4}\b",
            "phone": r"\b\d{3}-?\d{3}-?\d{4}\b",
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
            "ip_address": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
        }

        self.medical_keywords = [
            "diagnosis",
            "patient",
            "medical record",
            "prescription",
            "medication",
            "treatment",
            "symptoms",
            "disease",
            "illness",
            "health condition",
            "medical history",
            "doctor",
            "physician",
            "hospital",
            "clinic",
        ]

        self.compliance_rules = {
            "hipaa": {
                "description": "Health Insurance Portability and Accountability Act",
                "prohibited": [
                    "patient names",
                    "medical record numbers",
                    "health plan beneficiary numbers",
                ],
                "required_actions": ["anonymize", "redact", "encrypt"],
            },
            "gdpr": {
                "description": "General Data Protection Regulation",
                "prohibited": ["personal identifiers", "location data", "biometric data"],
                "required_actions": [
                    "consent verification",
                    "data minimization",
                    "right to deletion",
                ],
            },
            "pci": {
                "description": "Payment Card Industry Data Security Standard",
                "prohibited": ["full credit card numbers", "cvv codes", "cardholder data"],
                "required_actions": ["tokenization", "encryption", "access control"],
            },
        }


class GuardrailChecker:
    """Main guardrail checking engine"""

    def __init__(self, config: GuardrailConfig = None):
        self.config = config or GuardrailConfig()

    def check_pii_exposure(self, text: str) -> Dict[str, Any]:
        """Check for PII exposure in text"""
        violations = []

        for pii_type, pattern in self.config.pii_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                violations.append(
                    {
                        "type": "PII_EXPOSURE",
                        "category": pii_type,
                        "matches": len(matches),
                        "severity": "HIGH",
                        "description": f"Detected {pii_type} information",
                    }
                )

        return {
            "has_violations": len(violations) > 0,
            "violations": violations,
            "total_pii_detected": len(violations),
        }

    def check_medical_compliance(self, text: str) -> Dict[str, Any]:
        """Check for medical information compliance"""
        violations = []
        text_lower = text.lower()

        detected_medical_terms = []
        for keyword in self.config.medical_keywords:
            if keyword in text_lower:
                detected_medical_terms.append(keyword)

        if detected_medical_terms:
            violations.append(
                {
                    "type": "MEDICAL_INFORMATION",
                    "detected_terms": detected_medical_terms,
                    "severity": "MEDIUM",
                    "compliance_requirement": "HIPAA",
                    "description": "Medical information detected - requires compliance review",
                }
            )

        return {
            "has_violations": len(violations) > 0,
            "violations": violations,
            "medical_terms_detected": detected_medical_terms,
        }

    def apply_guardrails(self, text: str, compliance_mode: str = "strict") -> Dict[str, Any]:
        """Apply all guardrail checks and return results with recommendations"""
        pii_check = self.check_pii_exposure(text)
        medical_check = self.check_medical_compliance(text)

        all_violations = pii_check["violations"] + medical_check["violations"]

        # Generate recommendations
        recommendations = []
        sanitized_text = text

        if pii_check["has_violations"]:
            recommendations.append("Remove or redact PII information before sharing")
            # Basic sanitization
            for pii_type, pattern in self.config.pii_patterns.items():
                sanitized_text = re.sub(
                    pattern, f"[REDACTED_{pii_type.upper()}]", sanitized_text, flags=re.IGNORECASE
                )

        if medical_check["has_violations"]:
            recommendations.append("Ensure HIPAA compliance for medical information")
            recommendations.append("Consider anonymization of patient data")

        # Determine action based on compliance mode
        if compliance_mode == "strict" and all_violations:
            action = "BLOCK"
            message = "Output blocked due to compliance violations"
        elif compliance_mode == "moderate" and any(v["severity"] == "HIGH" for v in all_violations):
            action = "SANITIZE"
            message = "Output sanitized to remove high-risk information"
        else:
            action = "ALLOW"
            message = "Output approved"

        return {
            "action": action,
            "message": message,
            "original_text": text,
            "sanitized_text": sanitized_text,
            "compliance_mode": compliance_mode,
            "violations": all_violations,
            "recommendations": recommendations,
            "risk_score": len([v for v in all_violations if v["severity"] == "HIGH"]) * 3
            + len([v for v in all_violations if v["severity"] == "MEDIUM"]) * 1,
        }


def register_guardrail_resources(mcp: FastMCP):
    """Register guardrail resources with MCP server"""

    @mcp.resource("guardrail://config/pii")
    def get_pii_config() -> str:
        """
        Get PII detection configuration patterns and rules

        This resource provides configuration for detecting personally
        identifiable information in outputs.

        Keywords: guardrail, pii, privacy, security, compliance, detection
        Category: security
        """
        config = GuardrailConfig()
        return json.dumps(
            {
                "description": "PII Detection Patterns",
                "patterns": config.pii_patterns,
                "categories": list(config.pii_patterns.keys()),
                "usage": "Use these patterns to detect PII in text outputs",
            },
            indent=2,
        )

    @mcp.resource("guardrail://config/medical")
    def get_medical_config() -> str:
        """
        Get medical information compliance configuration

        This resource provides HIPAA and medical data compliance
        rules and detection keywords.

        Keywords: guardrail, medical, hipaa, compliance, healthcare, privacy
        Category: security
        """
        config = GuardrailConfig()
        return json.dumps(
            {
                "description": "Medical Information Compliance",
                "medical_keywords": config.medical_keywords,
                "compliance_rules": config.compliance_rules,
                "usage": "Use for HIPAA and medical data compliance checking",
            },
            indent=2,
        )

    @mcp.resource("guardrail://policies/compliance")
    def get_compliance_policies() -> str:
        """
        Get comprehensive compliance policies and enforcement rules

        This resource provides detailed compliance policies for
        different regulatory frameworks.

        Keywords: guardrail, compliance, policy, gdpr, hipaa, pci, enforcement
        Category: security
        """
        config = GuardrailConfig()
        return json.dumps(
            {
                "description": "Compliance Policy Framework",
                "policies": config.compliance_rules,
                "enforcement_modes": {
                    "strict": "Block any violations",
                    "moderate": "Sanitize high-risk content",
                    "permissive": "Log violations but allow",
                },
                "usage": "Configure compliance checking behavior",
            },
            indent=2,
        )

    @mcp.resource("guardrail://check/sample")
    def get_sample_check() -> str:
        """
        Get sample guardrail check results for testing

        This resource provides example guardrail check results
        to demonstrate the checking process.

        Keywords: guardrail, sample, test, example, check, demo
        Category: security
        """
        checker = GuardrailChecker()
        sample_text = (
            "Contact John Doe at 555-123-4567 or john.doe@example.com for patient medical records."
        )

        result = checker.apply_guardrails(sample_text, "strict")

        return json.dumps(
            {
                "description": "Sample Guardrail Check",
                "sample_input": sample_text,
                "check_result": result,
                "usage": "Example of guardrail checking process",
            },
            indent=2,
        )

    # Registration complete
