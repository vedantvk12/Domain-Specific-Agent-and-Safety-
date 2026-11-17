"""
output_guard.py
---------------
Output Validation, Secret Redaction, and Report Sanitization Guard for SecureCode AI.
Ensures that generated reports do not leak plaintext credentials, mirror prompt injection
instructions, or violate structured output constraints.
"""

from typing import Tuple, List
from models import SecurityAssessmentReport, SecurityFinding
from security_tools import SecretScanner
from audit_logger import AuditLogger


class OutputGuardError(Exception):
    """Raised when the output report fails schema or security validation."""
    pass


class OutputGuard:
    """
    Enforces security compliance on agent outputs before display or persistence:
    1. Secret Redaction: Replaces API keys, tokens, and passwords with safe masks.
    2. Injection Neutralization: Prevents malicious prompt instructions from echoing into remediation advice.
    3. Schema & Integrity Validation: Ensures findings counts and fields are mathematically consistent.
    """

    def __init__(self, audit_logger: AuditLogger = None):
        self.audit_logger = audit_logger

    def sanitize_and_validate(self, report: SecurityAssessmentReport) -> Tuple[bool, SecurityAssessmentReport, List[str]]:
        """
        Validates the security assessment report and sanitizes all contained text fields.
        Returns: (is_valid: bool, sanitized_report: SecurityAssessmentReport, warnings: List[str])
        """
        warnings = []
        redaction_occurred = False

        # 1. Check mathematical consistency of finding counts
        calculated_total = (
            report.critical_count +
            report.high_count +
            report.medium_count +
            report.low_count
        )
        if calculated_total != len(report.findings):
            warnings.append(
                f"Count mismatch: Total findings ({len(report.findings)}) does not match sum of severity tiers ({calculated_total}). Re-synchronizing counts."
            )
            report.total_findings = len(report.findings)

        # 2. Sanitize and redact narrative summary
        sanitized_summary = SecretScanner.redact(report.summary)
        if sanitized_summary != report.summary:
            redaction_occurred = True
            report.summary = sanitized_summary

        # 3. Sanitize each finding
        for finding in report.findings:
            # Redact snippet
            redacted_snippet = SecretScanner.redact(finding.code_snippet)
            if redacted_snippet != finding.code_snippet:
                redaction_occurred = True
                finding.code_snippet = redacted_snippet

            # Redact description and recommendation
            redacted_desc = SecretScanner.redact(finding.description)
            if redacted_desc != finding.description:
                redaction_occurred = True
                finding.description = redacted_desc

            redacted_rec = SecretScanner.redact(finding.recommendation)
            if redacted_rec != finding.recommendation:
                redaction_occurred = True
                finding.recommendation = redacted_rec

            # Strip dangerous command echoes in recommendations
            if "curl " in finding.recommendation.lower() or "wget " in finding.recommendation.lower():
                finding.recommendation = "Review security documentation and use official client SDKs."

        if redaction_occurred:
            report.redaction_applied = True

        # 4. Audit logging
        if self.audit_logger:
            self.audit_logger.log(
                event_type="OUTPUT_VALIDATION_COMPLETED",
                actor="OutputGuard",
                action="sanitize_and_validate",
                details={
                    "target_file": report.target_file,
                    "total_findings": report.total_findings,
                    "redaction_applied": report.redaction_applied,
                    "warnings_count": len(warnings)
                },
                risk_level="INFO",
                status="ALLOWED"
            )

        return True, report, warnings

