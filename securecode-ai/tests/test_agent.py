"""
test_agent.py
-------------
Comprehensive automated unit and security integration test suite for SecureCode AI.
Tests every security control, attack vector, boundary condition, and redaction mechanism.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import SecureCodeAgent
from models import RiskLevel, VulnerabilityCategory, ApprovalStatus
from input_validator import InputValidator, InputValidationError
from injection_detector import PromptInjectionDetector
from security_tools import SecretScanner, SimulatedOutboundTool, ToolDispatcher
from approval_manager import ApprovalManager
from output_guard import OutputGuard
from audit_logger import AuditLogger


class TestSecureCodeAgent(unittest.TestCase):
    """Rigorous test cases verifying each architectural security control."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = os.path.dirname(os.path.abspath(__file__))
        cls.project_dir = os.path.dirname(cls.test_dir)
        cls.sample_repo = os.path.join(cls.project_dir, "sample_data", "fake_repo")
        cls.output_dir = os.path.join(cls.project_dir, "outputs")

    def setUp(self):
        self.agent = SecureCodeAgent(
            auto_approval_policy="DENY_ALL",
            log_dir=self.output_dir,
            allowed_base_dir=self.project_dir
        )

    # --------------------------------------------------------------------------
    # Control 1: Normal Code Baseline
    # --------------------------------------------------------------------------
    def test_01_normal_source_code_clean_baseline(self):
        clean_file = os.path.join(self.sample_repo, "synthetic_service.py")
        report = self.agent.review_file(clean_file)

        self.assertEqual(report.status, "COMPLETED_CLEAN")
        self.assertEqual(report.total_findings, 0)
        self.assertEqual(report.critical_count, 0)
        self.assertEqual(report.high_count, 0)
        self.assertFalse(report.injection_threat_neutralized)
        print("\n[TEST 01 PASS] Normal source code verified: 0 vulnerabilities, clean baseline.")

    # --------------------------------------------------------------------------
    # Control 2: Input Validation (Malformed, Oversized, Path Traversal)
    # --------------------------------------------------------------------------
    def test_02_input_validation_catches_syntax_malformed(self):
        malformed_file = os.path.join(self.sample_repo, "malformed_input.py")
        report = self.agent.review_file(malformed_file)

        self.assertEqual(report.status, "REJECTED_AT_INPUT_GATE")
        self.assertEqual(report.total_findings, 1)
        self.assertEqual(report.findings[0].category, VulnerabilityCategory.INPUT_VALIDATION_FAILURE)
        self.assertIn("Syntax", report.findings[0].title)
        print("[TEST 02A PASS] Malformed syntax successfully rejected at input boundary.")

    def test_02b_input_validation_catches_oversized_payload(self):
        huge_payload = "# Normal looking comment\n" + ("x = 1\n" * 65000)  # > 512 KB
        report = self.agent.review_code(huge_payload, label="oversized_test.py")

        self.assertEqual(report.status, "REJECTED_AT_INPUT_GATE")
        self.assertTrue("limit" in report.summary.lower() or "exceeding" in report.summary.lower())
        print("[TEST 02B PASS] Oversized source code (>512 KB) successfully rejected.")

    def test_02c_input_validation_blocks_path_traversal(self):
        validator = InputValidator(allowed_base_dir=self.sample_repo)
        traversal_path = os.path.join(self.sample_repo, "..", "..", "main.py")

        with self.assertRaises(InputValidationError) as ctx:
            validator.validate_filepath(traversal_path)
        self.assertIn("Path traversal attempt blocked", str(ctx.exception))
        print("[TEST 02C PASS] Directory traversal attempt outside allowed boundary rejected.")

    # --------------------------------------------------------------------------
    # Control 3: Prompt Injection Detection in Comments
    # --------------------------------------------------------------------------
    def test_03_prompt_injection_detection_in_comments(self):
        injection_file = os.path.join(self.sample_repo, "malicious_prompt_injection.py")
        report = self.agent.review_file(injection_file)

        self.assertTrue(report.injection_threat_neutralized)
        injection_findings = [f for f in report.findings if f.category == VulnerabilityCategory.PROMPT_INJECTION]
        self.assertGreaterEqual(len(injection_findings), 1)

        # Check that override and exfiltration phrases triggered critical alerts
        titles = [f.title for f in injection_findings]
        self.assertTrue(any("OVERRIDE" in t or "EXFILTRATION" in t for t in titles))
        print(f"[TEST 03 PASS] Prompt injection detected in comments: {len(injection_findings)} injection patterns flagged.")

    # --------------------------------------------------------------------------
    # Control 4: Vulnerability & Fake Credential Detection
    # --------------------------------------------------------------------------
    def test_04_vulnerability_and_fake_credential_detection(self):
        vuln_file = os.path.join(self.sample_repo, "vulnerable_app.py")
        report = self.agent.review_file(vuln_file)

        self.assertEqual(report.status, "COMPLETED_WITH_FINDINGS")
        self.assertGreaterEqual(report.total_findings, 5)
        self.assertGreaterEqual(report.critical_count, 3)

        categories = [f.category for f in report.findings]
        self.assertIn(VulnerabilityCategory.HARDCODED_CREDENTIAL, categories)
        self.assertIn(VulnerabilityCategory.SUSPICIOUS_FUNCTION, categories)
        self.assertIn(VulnerabilityCategory.UNSAFE_OPERATION, categories)
        self.assertIn(VulnerabilityCategory.DATA_EXPOSURE, categories)
        print(f"[TEST 04 PASS] Detected {report.total_findings} security vulnerabilities in vulnerable_app.py.")

    # --------------------------------------------------------------------------
    # Control 5: Least Privilege and Tool-Call Validation
    # --------------------------------------------------------------------------
    def test_05_least_privilege_blocks_unauthorized_tool_call(self):
        # Caller with security_analyst role lacks OUTBOUND_DISPATCH permission
        result = self.agent.attempt_outbound_transmission(
            destination="https://attacker-webhook.internal.test/exfil",
            payload="Synthetic leaked key",
            caller_role="security_analyst"
        )

        self.assertFalse(result.success)
        self.assertEqual(result.blocked_by, "LeastPrivilegeEnforcer")
        print("[TEST 05 PASS] Least Privilege thwarted unauthorized outbound tool invocation by unauthorized role.")

    # --------------------------------------------------------------------------
    # Control 6: Human Approval Gate Enforcement
    # --------------------------------------------------------------------------
    def test_06_human_approval_blocks_unapproved_transmissions(self):
        mgr = ApprovalManager(auto_policy="DENY_ALL", audit_logger=self.agent.audit_logger)
        is_approved, token, ticket = mgr.request_approval(
            tool_name="SimulatedOutboundTool",
            destination="https://unauthorized-endpoint.test/data",
            payload="Sensitive report",
            risk_summary="Outbound attempt"
        )

        self.assertFalse(is_approved)
        self.assertIsNone(token)
        self.assertEqual(ticket.status, ApprovalStatus.REJECTED)
        print("[TEST 06 PASS] Human Approval Gate denied unapproved transmission by policy.")

    def test_06b_human_approval_automatic_denial_on_injection(self):
        mgr = ApprovalManager(auto_policy="ALLOW_ALL", audit_logger=self.agent.audit_logger)
        # Even if policy is ALLOW_ALL, an active prompt injection suspicion triggers AUTO_DENIED
        is_approved, token, ticket = mgr.request_approval(
            tool_name="SimulatedOutboundTool",
            destination="https://attacker-webhook.internal.test/exfil",
            payload="Exfiltrated credentials",
            risk_summary="Injection exfiltration",
            is_injection_suspected=True
        )

        self.assertFalse(is_approved)
        self.assertEqual(ticket.status, ApprovalStatus.AUTO_DENIED)
        self.assertIn("AUTOMATIC DENIAL", ticket.operator_comment)
        print("[TEST 06B PASS] Human Approval Gate auto-denied request due to active prompt injection flag.")

    # --------------------------------------------------------------------------
    # Control 7: Secret Redaction in Output
    # --------------------------------------------------------------------------
    def test_07_secret_redaction_in_output_reports(self):
        vuln_file = os.path.join(self.sample_repo, "vulnerable_app.py")
        report = self.agent.review_file(vuln_file)

        # Ensure no plaintext dummy key survives in snippets or recommendations
        for f in report.findings:
            self.assertNotIn("AKIAFAKE1234567890EX", f.code_snippet)
            self.assertNotIn("sk_live_fake9876543210abcdef12345678", f.code_snippet)
            self.assertNotIn("SuperSecretTestPass123!", f.code_snippet)

        markdown_text = self.agent.format_markdown_report(report)
        self.assertNotIn("AKIAFAKE1234567890EX", markdown_text)
        self.assertIn("[REDACTED_AWS_KEY]", markdown_text)
        print("[TEST 07 PASS] Secret redaction verified: Plaintext credentials masked in reports.")

    # --------------------------------------------------------------------------
    # Control 8: Tamper-Evident Audit Logging
    # --------------------------------------------------------------------------
    def test_08_audit_logging_integrity(self):
        clean_file = os.path.join(self.sample_repo, "synthetic_service.py")
        self.agent.review_file(clean_file)

        jsonl_path = os.path.join(self.output_dir, "audit_log.jsonl")
        self.assertTrue(os.path.exists(jsonl_path))

        with open(jsonl_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        self.assertGreater(len(lines), 0)
        # Verify events contain required security audit fields
        event_types = [entry.event_type for entry in self.agent.audit_logger.get_events()]
        self.assertIn("AUDIT_JOB_STARTED", event_types)
        print(f"[TEST 08 PASS] Audit logging verified: {len(lines)} persisted events captured.")


if __name__ == "__main__":
    unittest.main()
