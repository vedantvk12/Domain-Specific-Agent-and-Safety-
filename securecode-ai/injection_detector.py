"""
injection_detector.py
---------------------
Prompt Injection and Malicious Comment Instruction Detector for SecureCode AI.
Treats all source-code comments, docstrings, and embedded string literals as UNTRUSTED input.
Scans for adversarial jailbreaks, system prompt overrides, exfiltration commands,
and covert instructions attempting to manipulate agent reasoning or invoke tools.
"""

import io
import re
import tokenize
from typing import List, Dict, Any, Tuple, Optional
from models import SecurityFinding, VulnerabilityCategory, RiskLevel
from audit_logger import AuditLogger


class PromptInjectionDetector:
    """
    Analyzes comments and string literals in source code to detect indirect prompt injection attacks.
    Applies regex signatures, delimiter detection, and imperative exfiltration heuristic scoring.
    """

    INJECTION_PATTERNS = [
        # Direct override / jailbreak signatures
        (r"(?i)\bignore\s+(all\s+)?(previous|prior|above)\s+(instructions|rules|constraints|directives)", "PROMPT_INJECTION_OVERRIDE", "High-confidence system prompt override phrase detected"),
        (r"(?i)\bdisregard\s+(all\s+)?(previous|prior|system|security)\s+(rules|prompts|guidelines)", "PROMPT_INJECTION_DISREGARD", "Disregard security directives signature"),
        (r"(?i)\bbypass\s+(all\s+)?(security|safety|validation|sandbox)\s+(checks|rules|controls)", "PROMPT_INJECTION_BYPASS", "Security control bypass attempt in comment"),
        (r"(?i)\boverride\s+system\s+prompt\b", "PROMPT_INJECTION_SYSTEM_OVERRIDE", "Direct system prompt override indicator"),
        
        # Exfiltration / Outbound instruction triggers
        (r"(?i)\b(print|leak|reveal|dump|expose|show|output)\s+(the\s+)?(stored|hidden|synthetic|private)?\s*(api[_\s-]?key|secret|password|credential|token)", "EXFILTRATION_INSTRUCTION", "Instruction attempting to reveal or print stored secrets"),
        (r"(?i)\b(transmit|dispatch|exfiltrate|send|upload|post)\s+.*?\b(to|via)\s+(https?://|[a-z0-9.-]+\.internal|[a-z0-9.-]+\.test|webhook|email)", "OUTBOUND_EXFILTRATION_TRIGGER", "Malicious command attempting outbound transmission of sensitive data"),
        (r"(?i)\bcurl\s+-X\s+POST\b|\bwget\s+--post-data\b", "COVERT_CLI_EXECUTION", "Covert shell exfiltration command inside comment"),
        
        # Role spoofing & synthetic delimiter injection
        (r"(?i)\[MAINTAINER\s+OVERRIDE\]|\[ADMIN\s+DIRECTIVE\]|\[SYSTEM\s+PROMPT\]", "ROLE_SPOOFING_DELIMITER", "Adversarial delimiter attempting privilege escalation / role spoofing"),
        (r"(?i)<script.*?>|<!--\s*#exec\b", "MARKUP_INJECTION_PAYLOAD", "Code injection / markup escape sequence in comments"),
    ]

    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        self.audit_logger = audit_logger

    def extract_comments_and_docstrings(self, source_code: str) -> List[Dict[str, Any]]:
        """
        Parses source code token stream to extract comments and standalone docstrings with line numbers.
        """
        extracted = []
        try:
            tokens = tokenize.tokenize(io.BytesIO(source_code.encode("utf-8")).readline)
            for token in tokens:
                if token.type == tokenize.COMMENT:
                    extracted.append({
                        "type": "comment",
                        "text": token.string,
                        "line": token.start[0],
                        "end_line": token.end[0]
                    })
                elif token.type == tokenize.STRING:
                    # Capture multiline strings that often serve as docstrings or embedded instructions
                    text_content = token.string.strip()
                    if text_content.startswith(('"""', "'''")):
                        extracted.append({
                            "type": "docstring",
                            "text": text_content,
                            "line": token.start[0],
                            "end_line": token.end[0]
                        })
        except Exception:
            # Fallback to regex line scanning if tokenization encounters unexpected edge cases
            for idx, line in enumerate(source_code.splitlines(), start=1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    extracted.append({
                        "type": "comment",
                        "text": stripped,
                        "line": idx,
                        "end_line": idx
                    })
        return extracted

    def scan(self, source_code: str, source_name: str = "source_file.py") -> Tuple[bool, List[SecurityFinding], float]:
        """
        Scans all comments and docstrings in the code for adversarial prompt injection payloads.
        Returns:
            - is_threat_detected: bool
            - findings: List[SecurityFinding]
            - max_threat_score: float (0.0 to 1.0)
        """
        items = self.extract_comments_and_docstrings(source_code)
        findings: List[SecurityFinding] = []
        threat_scores: List[float] = [0.0]

        finding_counter = 1

        for item in items:
            raw_text = item["text"]
            line_no = item["line"]

            for pattern, rule_code, desc in self.INJECTION_PATTERNS:
                match = re.search(pattern, raw_text)
                if match:
                    score = 0.95 if "EXFILTRATION" in rule_code or "OVERRIDE" in rule_code else 0.80
                    threat_scores.append(score)

                    finding_id = f"INJ-{finding_counter:03d}"
                    finding_counter += 1

                    risk_level = RiskLevel.CRITICAL if score >= 0.90 else RiskLevel.HIGH

                    finding = SecurityFinding(
                        finding_id=finding_id,
                        title=f"Adversarial Prompt Injection: {rule_code}",
                        category=VulnerabilityCategory.PROMPT_INJECTION,
                        risk_level=risk_level,
                        line_number=line_no,
                        code_snippet=raw_text[:160],
                        description=(
                            f"{desc}. The untrusted comment at line {line_no} contains instructions designed "
                            f"to subvert LLM decision boundaries, override security constraints, or trigger "
                            f"unauthorized external tool actions."
                        ),
                        recommendation=(
                            "Treat all comments and external text as untrusted data. Strip or sanitize comment "
                            "instructions before submitting prompts to language models. Never allow unverified "
                            "code comments to influence agent tool invocation or security enforcement policy."
                        ),
                        cwe_id="CWE-116"  # Improper Encoding or Handling of Delimiters / Injection
                    )
                    findings.append(finding)

                    if self.audit_logger:
                        self.audit_logger.log(
                            event_type="PROMPT_INJECTION_DETECTED",
                            actor="PromptInjectionDetector",
                            action="scan_comment",
                            details={
                                "file": source_name,
                                "line": line_no,
                                "rule_code": rule_code,
                                "matched_text": match.group(0),
                                "threat_score": score
                            },
                            risk_level="CRITICAL" if risk_level == RiskLevel.CRITICAL else "HIGH",
                            status="FLAGGED"
                        )

        is_threat = len(findings) > 0
        overall_score = max(threat_scores)
        return is_threat, findings, overall_score

