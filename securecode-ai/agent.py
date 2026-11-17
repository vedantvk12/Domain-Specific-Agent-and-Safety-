"""
agent.py
--------
Core SecureCode AI Agent Orchestrator.
Integrates input validation, prompt injection detection, AST static analysis,
secret scanning, tool authorization, human-in-the-loop approval, and output redaction
into a unified, defensive, domain-specific security review pipeline.
"""

import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from models import (
    RiskLevel,
    VulnerabilityCategory,
    SecurityFinding,
    SecurityAssessmentReport,
    ToolCallRequest,
    ToolCallResult,
    ApprovalStatus
)
from audit_logger import AuditLogger
from input_validator import InputValidator, InputValidationError
from injection_detector import PromptInjectionDetector
from security_tools import (
    SecretScanner,
    ASTVulnerabilityScanner,
    SimulatedOutboundTool,
    ToolDispatcher
)
from approval_manager import ApprovalManager
from output_guard import OutputGuard


class SecureCodeAgent:
    """
    Autonomous domain-specific AI agent for secure code auditing and risk detection.
    Operates under strict multi-layer defense-in-depth principles.
    """

    def __init__(
        self,
        auto_approval_policy: str = "DENY_ALL",
        log_dir: str = "outputs",
        allowed_base_dir: Optional[str] = None
    ):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)

        self.audit_logger = AuditLogger(log_dir=log_dir)
        self.input_validator = InputValidator(audit_logger=self.audit_logger, allowed_base_dir=allowed_base_dir)
        self.injection_detector = PromptInjectionDetector(audit_logger=self.audit_logger)
        self.secret_scanner = SecretScanner(audit_logger=self.audit_logger)
        self.ast_scanner = ASTVulnerabilityScanner(audit_logger=self.audit_logger)
        self.outbound_tool = SimulatedOutboundTool(
            log_path=os.path.join(self.log_dir, "simulated_outbound_transmissions.log"),
            audit_logger=self.audit_logger
        )
        self.approval_manager = ApprovalManager(auto_policy=auto_approval_policy, audit_logger=self.audit_logger)
        self.tool_dispatcher = ToolDispatcher(outbound_tool=self.outbound_tool, audit_logger=self.audit_logger)
        self.output_guard = OutputGuard(audit_logger=self.audit_logger)

    def review_file(self, filepath: str) -> SecurityAssessmentReport:
        """
        Executes end-to-end security audit on a physical source file.
        """
        self.audit_logger.log(
            event_type="AUDIT_JOB_STARTED",
            actor="SecureCodeAgent",
            action="review_file",
            details={"filepath": filepath},
            risk_level="INFO",
            status="INITIATED"
        )

        # Step 1: Input Validation
        is_valid, err_msg, content, ast_tree = self.input_validator.validate_file(filepath)
        filename = os.path.basename(filepath)

        if not is_valid:
            sub_type = "Syntax Error" if "syntax" in (err_msg or "").lower() else "Input Boundary Violation"
            # Generate rejection report
            finding = SecurityFinding(
                finding_id="VAL-001",
                title=f"Input Validation Rejection: {sub_type}",
                category=VulnerabilityCategory.INPUT_VALIDATION_FAILURE,
                risk_level=RiskLevel.HIGH,
                line_number=None,
                code_snippet="",
                description=err_msg or "File failed input security bounds validation.",
                recommendation="Provide valid, UTF-8 encoded Python source code under 512 KB.",
                cwe_id="CWE-20"
            )
            report = SecurityAssessmentReport(
                target_file=filename,
                scan_timestamp=datetime.now(timezone.utc).isoformat(),
                status="REJECTED_AT_INPUT_GATE",
                total_findings=1,
                high_count=1,
                findings=[finding],
                summary=f"Audit halted: {err_msg}",
                redaction_applied=False,
                injection_threat_neutralized=False
            )
            _, sanitized_report, _ = self.output_guard.sanitize_and_validate(report)
            return sanitized_report

        return self._run_analysis_pipeline(content, filename, ast_tree)

    def review_code(self, source_code: str, label: str = "snippet.py") -> SecurityAssessmentReport:
        """
        Executes end-to-end security audit on in-memory source code string.
        """
        self.audit_logger.log(
            event_type="AUDIT_JOB_STARTED",
            actor="SecureCodeAgent",
            action="review_code",
            details={"label": label, "size_chars": len(source_code)},
            risk_level="INFO",
            status="INITIATED"
        )

        # Step 1: Input Validation
        is_valid, err_msg, ast_tree = self.input_validator.validate_content(source_code, source_label=label)
        if not is_valid:
            finding = SecurityFinding(
                finding_id="VAL-001",
                title="Input Content Validation Rejection",
                category=VulnerabilityCategory.INPUT_VALIDATION_FAILURE,
                risk_level=RiskLevel.HIGH,
                line_number=None,
                code_snippet="",
                description=err_msg or "Content failed input security bounds validation.",
                recommendation="Ensure source string is well-formed Python syntax under 512 KB.",
                cwe_id="CWE-20"
            )
            report = SecurityAssessmentReport(
                target_file=label,
                scan_timestamp=datetime.now(timezone.utc).isoformat(),
                status="REJECTED_AT_INPUT_GATE",
                total_findings=1,
                high_count=1,
                findings=[finding],
                summary=f"Audit halted: {err_msg}",
                redaction_applied=False,
                injection_threat_neutralized=False
            )
            _, sanitized_report, _ = self.output_guard.sanitize_and_validate(report)
            return sanitized_report

        return self._run_analysis_pipeline(source_code, label, ast_tree)

    def _run_analysis_pipeline(self, source_code: str, label: str, ast_tree: Optional[Any]) -> SecurityAssessmentReport:
        """Internal execution pipeline for validated source code."""
        all_findings: List[SecurityFinding] = []

        # Step 2: Prompt Injection Detection (Treat comments as untrusted input)
        has_injection, injection_findings, threat_score = self.injection_detector.scan(source_code, source_name=label)
        all_findings.extend(injection_findings)

        # Step 3: Hardcoded Secret Scanning
        secret_findings = self.secret_scanner.scan(source_code, filename=label)
        all_findings.extend(secret_findings)

        # Step 4: AST Vulnerability Scanning (if syntax tree available)
        if ast_tree:
            ast_findings = self.ast_scanner.scan(ast_tree, source_code, filename=label)
            all_findings.extend(ast_findings)

        # Step 5: Check if Prompt Injection Attempted Outbound Transmission
        # If an injection payload requested exfiltration, the agent simulates the attack handling:
        # The agent recognizes the adversarial instruction, records it as a blocked attack,
        # and refuses to invoke outbound tools.
        injection_neutralized = False
        if has_injection:
            injection_neutralized = True
            self.audit_logger.log(
                event_type="INJECTION_ATTACK_NEUTRALIZED",
                actor="SecureCodeAgent",
                action="defend_against_prompt_injection",
                details={
                    "file": label,
                    "threat_score": threat_score,
                    "action_taken": "Quarantined comment instructions; prevented tool dispatch; redacted secrets"
                },
                risk_level="CRITICAL",
                status="BLOCKED"
            )

        # Step 6: Tally Risk Counts
        crit_count = sum(1 for f in all_findings if f.risk_level == RiskLevel.CRITICAL)
        high_count = sum(1 for f in all_findings if f.risk_level == RiskLevel.HIGH)
        med_count = sum(1 for f in all_findings if f.risk_level == RiskLevel.MEDIUM)
        low_count = sum(1 for f in all_findings if f.risk_level == RiskLevel.LOW)

        # Step 7: Draft Executive Summary
        if all_findings:
            summary = (
                f"Security audit completed for '{label}'. Identified {len(all_findings)} security findings "
                f"({crit_count} CRITICAL, {high_count} HIGH, {med_count} MEDIUM, {low_count} LOW). "
            )
            if has_injection:
                summary += "CRITICAL: Malicious prompt injection attempt was detected in comments and neutralized. "
            if crit_count > 0:
                summary += "Immediate remediation is required for critical vulnerabilities prior to deployment."
            else:
                summary += "Review recommended code modifications to enhance application posture."
        else:
            summary = f"Security audit completed for '{label}'. Clean baseline: No vulnerabilities or security risks detected."

        raw_report = SecurityAssessmentReport(
            target_file=label,
            scan_timestamp=datetime.now(timezone.utc).isoformat(),
            status="COMPLETED_WITH_FINDINGS" if all_findings else "COMPLETED_CLEAN",
            total_findings=len(all_findings),
            critical_count=crit_count,
            high_count=high_count,
            medium_count=med_count,
            low_count=low_count,
            findings=all_findings,
            summary=summary,
            redaction_applied=False,
            injection_threat_neutralized=injection_neutralized
        )

        # Step 8: Output Guard Sanitization & Validation
        _, sanitized_report, _ = self.output_guard.sanitize_and_validate(raw_report)

        self.audit_logger.log(
            event_type="AUDIT_JOB_COMPLETED",
            actor="SecureCodeAgent",
            action="finalize_report",
            details={
                "target_file": label,
                "findings": sanitized_report.total_findings,
                "critical": sanitized_report.critical_count,
                "high": sanitized_report.high_count
            },
            risk_level="INFO",
            status="ALLOWED"
        )

        return sanitized_report

    def attempt_outbound_transmission(
        self,
        destination: str,
        payload: str,
        protocol: str = "webhook",
        caller_role: str = "untrusted_code_executor",
        is_injection_suspected: bool = False
    ) -> ToolCallResult:
        """
        Directly executes the Three Ingredients interaction flow to demonstrate
        how security controls intercept and thwart data exfiltration attacks.
        """
        call_id = f"CALL-{datetime.now().strftime('%H%M%S%f')[:8]}"
        self.audit_logger.log(
            event_type="OUTBOUND_CALL_REQUESTED",
            actor="SecureCodeAgent",
            action="attempt_outbound_transmission",
            details={
                "call_id": call_id,
                "destination": destination,
                "caller_role": caller_role,
                "is_injection_suspected": is_injection_suspected
            },
            risk_level="HIGH",
            status="FLAGGED"
        )

        # Gate 1: Human Approval Check
        is_approved, auth_token, ticket = self.approval_manager.request_approval(
            tool_name="SimulatedOutboundTool",
            destination=destination,
            payload=payload,
            risk_summary="Attempted simulated outbound transmission of source code / key data",
            is_injection_suspected=is_injection_suspected
        )

        # Gate 2: Tool-Call Dispatcher & Least Privilege Enforcement
        tool_req = ToolCallRequest(
            call_id=call_id,
            tool_name="SimulatedOutboundTool",
            caller_role=caller_role,
            parameters={"destination": destination, "payload": payload, "protocol": protocol},
            auth_token=auth_token,
            justification="Transmitting security report or exfiltrating data"
        )

        result = self.tool_dispatcher.validate_and_execute(tool_req, approval_verified=is_approved)
        return result

    def format_markdown_report(self, report: SecurityAssessmentReport) -> str:
        """Generates an undergraduate-readable markdown representation of the audit report."""
        lines = []
        lines.append(f"# SecureCode AI - Security Assessment Report")
        lines.append(f"**Target File:** `{report.target_file}`  ")
        lines.append(f"**Scan Timestamp:** `{report.scan_timestamp}`  ")
        lines.append(f"**Audit Status:** `{report.status}`  ")
        lines.append(f"**Redaction Applied:** `{report.redaction_applied}`  ")
        lines.append(f"**Prompt Injection Neutralized:** `{report.injection_threat_neutralized}`\n")

        lines.append("## Executive Summary")
        lines.append(report.summary + "\n")

        lines.append("## Risk Severity Breakdown")
        lines.append(f"- **CRITICAL:** {report.critical_count}")
        lines.append(f"- **HIGH:** {report.high_count}")
        lines.append(f"- **MEDIUM:** {report.medium_count}")
        lines.append(f"- **LOW:** {report.low_count}")
        lines.append(f"- **TOTAL FINDINGS:** {report.total_findings}\n")

        if report.findings:
            lines.append("## Detailed Vulnerability Findings\n")
            for idx, f in enumerate(report.findings, start=1):
                lines.append(f"### {idx}. [{f.risk_level.value}] {f.title} ({f.finding_id})")
                lines.append(f"- **Category:** `{f.category.value}`")
                lines.append(f"- **CWE ID:** `{f.cwe_id or 'N/A'}`")
                lines.append(f"- **Line Number:** `{f.line_number or 'Global / Architecture'}`")
                lines.append(f"- **Code Snippet:**")
                lines.append(f"  ```python\n  {f.code_snippet}\n  ```")
                lines.append(f"- **Vulnerability Description:** {f.description}")
                lines.append(f"- **Remediation Advice:** {f.recommendation}\n")
        else:
            lines.append("No security issues detected. Target conforms to clean baseline requirements.\n")

        return "\n".join(lines)
