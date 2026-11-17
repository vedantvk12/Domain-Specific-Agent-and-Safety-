"""
security_tools.py
-----------------
Security Analysis Tools and Tool-Call Validation Engine for SecureCode AI.
Contains:
1. SecretScanner: Regex & entropy-based credential detector and redactor.
2. ASTVulnerabilityScanner: AST analysis for dangerous sinks, unsafe operations, and data leakage.
3. SimulatedOutboundTool: Safe simulated outbound channel logging attempted dispatches locally.
4. ToolDispatcher: Enforces Least Privilege and Tool-Call Validation.
"""

import ast
import os
import re
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from models import (
    SecurityFinding,
    VulnerabilityCategory,
    RiskLevel,
    ToolCallRequest,
    ToolCallResult,
    ToolPermission
)
from audit_logger import AuditLogger


class SecretScanner:
    """
    Detects hardcoded credentials, API keys, tokens, and sensitive strings.
    Provides sanitization and redaction capabilities to protect confidential data.
    """

    SECRET_PATTERNS = [
        (r"AKIA[0-9A-Z]{16}", "AWS_ACCESS_KEY_ID", RiskLevel.CRITICAL, "CWE-798", "Use AWS IAM roles or environment variables"),
        (r"sk_live_[0-9a-zA-Z]{24,}", "STRIPE_SECRET_KEY", RiskLevel.CRITICAL, "CWE-798", "Store Stripe API secret in AWS Secrets Manager or Vault"),
        (r"ghp_[0-9a-zA-Z]{36}", "GITHUB_PERSONAL_ACCESS_TOKEN", RiskLevel.CRITICAL, "CWE-798", "Rotate GitHub token and store in encrypted CI secrets"),
        (r"(?i)(postgres|mysql|mongodb|redis)://[a-zA-Z0-9_\-]+:[^@\s]+@[a-zA-Z0-9_\.\-]+", "DATABASE_URI_CREDENTIALS", RiskLevel.HIGH, "CWE-312", "Pass database connection credentials via encrypted environment variables"),
        (r"(?i)(api[_\s-]?key|secret[_\s-]?key|auth[_\s-]?token|private[_\s-]?key)\s*=\s*['\"][0-9a-zA-Z_\-\.]{16,}['\"]", "GENERIC_API_SECRET", RiskLevel.HIGH, "CWE-798", "Externalize hardcoded secrets into secure key vaults"),
        (r"(?i)(password|passwd|pwd)\s*=\s*['\"][^'\"]{6,}['\"]", "HARDCODED_PASSWORD", RiskLevel.HIGH, "CWE-259", "Never hardcode passwords in source code; use secret managers")
    ]

    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        self.audit_logger = audit_logger

    def scan(self, source_code: str, filename: str = "source.py") -> List[SecurityFinding]:
        """Scans source code line by line for hardcoded credentials."""
        findings = []
        lines = source_code.splitlines()

        counter = 1
        for line_idx, line in enumerate(lines, start=1):
            # Skip pure comments if needed, but in code review comments may also leak keys
            for pattern, sec_type, risk, cwe, fix in self.SECRET_PATTERNS:
                matches = re.finditer(pattern, line)
                for match in matches:
                    matched_str = match.group(0)
                    finding_id = f"SEC-{counter:03d}"
                    counter += 1

                    redacted_snippet = self.redact(line)
                    finding = SecurityFinding(
                        finding_id=finding_id,
                        title=f"Hardcoded Credential Detected: {sec_type}",
                        category=VulnerabilityCategory.HARDCODED_CREDENTIAL,
                        risk_level=risk,
                        line_number=line_idx,
                        code_snippet=redacted_snippet,
                        description=(
                            f"Detected plaintext credential matching {sec_type} pattern at line {line_idx}. "
                            f"Hardcoding secrets in source code risks immediate credential leakage, lateral "
                            f"movement, and unauthorized cloud infrastructure compromise."
                        ),
                        recommendation=fix,
                        cwe_id=cwe
                    )
                    findings.append(finding)

                    if self.audit_logger:
                        self.audit_logger.log(
                            event_type="SECRET_DETECTED",
                            actor="SecretScanner",
                            action="scan_line",
                            details={
                                "file": filename,
                                "line": line_idx,
                                "secret_type": sec_type,
                                "redacted_sample": self.redact(matched_str)
                            },
                            risk_level=risk.value,
                            status="FLAGGED"
                        )
        return findings

    @classmethod
    def redact(cls, text: str) -> str:
        """Replaces sensitive patterns with generic redacted placeholders."""
        redacted = text
        redacted = re.sub(r"AKIA[0-9A-Z]{16}", "[REDACTED_AWS_KEY]", redacted)
        redacted = re.sub(r"sk_live_[0-9a-zA-Z]{24,}", "[REDACTED_STRIPE_KEY]", redacted)
        redacted = re.sub(r"ghp_[0-9a-zA-Z]{36}", "[REDACTED_GITHUB_TOKEN]", redacted)
        redacted = re.sub(r"(?i)(postgres|mysql|mongodb|redis)://([a-zA-Z0-9_\-]+):([^@\s]+)@", r"\1://\2:[REDACTED_PASSWORD]@", redacted)
        redacted = re.sub(
            r"(?i)(api[_\s-]?key|secret[_\s-]?key|auth[_\s-]?token|private[_\s-]?key)\s*=\s*['\"][0-9a-zA-Z_\-\.]{16,}['\"]",
            r"\1 = '[REDACTED_SECRET]'",
            redacted
        )
        redacted = re.sub(
            r"(?i)(password|passwd|pwd)\s*=\s*['\"][^'\"]{6,}['\"]",
            r"\1 = '[REDACTED_PASSWORD]'",
            redacted
        )
        return redacted


class ASTVulnerabilityScanner:
    """
    Performs Abstract Syntax Tree (AST) static analysis on parsed Python code to detect:
    - Suspicious functions: eval(), exec(), compile()
    - Unsafe operations: os.system(), subprocess.Popen(..., shell=True), pickle.loads()
    - SQL injection: string formatting inside db cursor execution
    - Data exposure: print/logging of sensitive variables
    - Insecure algorithms: MD5/SHA1 for cryptographic security
    """

    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        self.audit_logger = audit_logger

    def scan(self, tree: ast.AST, source_code: str, filename: str = "source.py") -> List[SecurityFinding]:
        findings: List[SecurityFinding] = []
        counter = 1
        lines = source_code.splitlines()

        def get_line_snippet(lineno: Optional[int]) -> str:
            if lineno and 1 <= lineno <= len(lines):
                return SecretScanner.redact(lines[lineno - 1].strip())
            return ""

        for node in ast.walk(tree):
            # 1. Suspicious function calls: eval, exec, compile
            if isinstance(node, ast.Call):
                func_name = None
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                lineno = getattr(node, "lineno", None)
                snippet = get_line_snippet(lineno)

                # eval() / exec()
                if func_name in ("eval", "exec", "compile"):
                    findings.append(SecurityFinding(
                        finding_id=f"AST-{counter:03d}",
                        title=f"Arbitrary Code Execution via {func_name}()",
                        category=VulnerabilityCategory.SUSPICIOUS_FUNCTION,
                        risk_level=RiskLevel.CRITICAL,
                        line_number=lineno,
                        code_snippet=snippet,
                        description=(
                            f"Invocation of dynamic execution primitive '{func_name}()' at line {lineno}. "
                            f"Passing untrusted inputs into dynamic evaluators leads directly to Remote Code Execution (RCE)."
                        ),
                        recommendation="Refactor dynamic evaluation to use safe parsers like ast.literal_eval() or deterministic dispatchers.",
                        cwe_id="CWE-95"
                    ))
                    counter += 1

                # os.system()
                elif func_name == "system" and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                    findings.append(SecurityFinding(
                        finding_id=f"AST-{counter:03d}",
                        title="Command Injection Sink via os.system()",
                        category=VulnerabilityCategory.UNSAFE_OPERATION,
                        risk_level=RiskLevel.CRITICAL,
                        line_number=lineno,
                        code_snippet=snippet,
                        description=(
                            f"Usage of 'os.system()' at line {lineno}. Executes commands directly in shell without input escaping, "
                            f"exposing the host environment to shell injection vulnerabilities."
                        ),
                        recommendation="Replace os.system with subprocess.run() without shell=True, passing arguments as a sanitized list.",
                        cwe_id="CWE-78"
                    ))
                    counter += 1

                # subprocess with shell=True
                elif func_name in ("Popen", "call", "run", "check_output"):
                    for kw in node.keywords:
                        if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                            findings.append(SecurityFinding(
                                finding_id=f"AST-{counter:03d}",
                                title=f"Insecure Shell Execution: subprocess.{func_name}(shell=True)",
                                category=VulnerabilityCategory.UNSAFE_OPERATION,
                                risk_level=RiskLevel.CRITICAL,
                                line_number=lineno,
                                code_snippet=snippet,
                                description=(
                                    f"Subprocess invoked with 'shell=True' at line {lineno}. Spawns an intermediary shell process, "
                                    f"enabling attackers to chain arbitrary OS commands via metacharacters (; & | `)."
                                ),
                                recommendation="Set shell=False and pass executable arguments as a list of validated strings.",
                                cwe_id="CWE-78"
                            ))
                            counter += 1

                # pickle.loads / pickle.load
                elif func_name in ("loads", "load") and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == "pickle":
                    findings.append(SecurityFinding(
                        finding_id=f"AST-{counter:03d}",
                        title="Insecure Deserialization via pickle",
                        category=VulnerabilityCategory.UNSAFE_OPERATION,
                        risk_level=RiskLevel.HIGH,
                        line_number=lineno,
                        code_snippet=snippet,
                        description=(
                            f"Unsafe deserialization sink 'pickle.{func_name}()' at line {lineno}. Deserializing untrusted pickle streams "
                            f"can trigger arbitrary Python object instantiation and code execution via __reduce__."
                        ),
                        recommendation="Use safe serialization formats like JSON, Protocol Buffers, or cryptographically signed schemas.",
                        cwe_id="CWE-502"
                    ))
                    counter += 1

                # Raw SQL formatting in execute()
                elif func_name == "execute":
                    if node.args and isinstance(node.args[0], (ast.JoinedStr, ast.BinOp)):
                        findings.append(SecurityFinding(
                            finding_id=f"AST-{counter:03d}",
                            title="Potential SQL Injection via Dynamic String Formatting",
                            category=VulnerabilityCategory.UNSAFE_OPERATION,
                            risk_level=RiskLevel.CRITICAL,
                            line_number=lineno,
                            code_snippet=snippet,
                            description=(
                                f"SQL execution method invoked with dynamic formatted string or string concatenation at line {lineno}. "
                                f"Allows attackers to manipulate query structure and exfiltrate database contents."
                            ),
                            recommendation="Utilize parameterized queries with query placeholders (e.g., cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,)))",
                            cwe_id="CWE-89"
                        ))
                        counter += 1

                # Weak hashing (MD5 / SHA1)
                elif func_name in ("md5", "sha1") and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == "hashlib":
                    findings.append(SecurityFinding(
                        finding_id=f"AST-{counter:03d}",
                        title=f"Weak Cryptographic Hash Algorithm: hashlib.{func_name}()",
                        category=VulnerabilityCategory.UNSAFE_OPERATION,
                        risk_level=RiskLevel.LOW,
                        line_number=lineno,
                        code_snippet=snippet,
                        description=(
                            f"Weak hash function '{func_name}' at line {lineno}. Collision resistance is broken; unsuitable for cryptographic signatures or passwords."
                        ),
                        recommendation="Upgrade to SHA-256 (hashlib.sha256()) for integrity checks, or Argon2id/bcrypt for password hashing.",
                        cwe_id="CWE-328"
                    ))
                    counter += 1

                # Data exposure via print/logging of sensitive variable names
                elif func_name in ("print", "debug", "info"):
                    # Check if args contain sensitive identifier references
                    for arg in node.args:
                        arg_str = ast.unparse(arg).lower() if hasattr(ast, "unparse") else ""
                        if any(k in arg_str for k in ("password", "secret", "api_key", "token", "credential")):
                            findings.append(SecurityFinding(
                                finding_id=f"AST-{counter:03d}",
                                title=f"Potential Sensitive Data Exposure via {func_name}()",
                                category=VulnerabilityCategory.DATA_EXPOSURE,
                                risk_level=RiskLevel.MEDIUM,
                                line_number=lineno,
                                code_snippet=snippet,
                                description=(
                                    f"Sensitive variable logged or printed to stdout at line {lineno}. Printing unmasked secrets risks "
                                    f"exposing them in application logs, terminal records, and monitoring aggregators."
                                ),
                                recommendation="Redact or mask sensitive variables before logging, or omit credentials entirely from output streams.",
                                cwe_id="CWE-532"
                            ))
                            counter += 1
                            break

        if self.audit_logger:
            self.audit_logger.log(
                event_type="AST_SCAN_COMPLETE",
                actor="ASTVulnerabilityScanner",
                action="scan",
                details={"file": filename, "findings_count": len(findings)},
                risk_level="INFO",
                status="ALLOWED"
            )

        return findings


class SimulatedOutboundTool:
    """
    Simulated outbound email/webhook transmission tool.
    SAFETY DESIGN:
    - Never communicates over real external networks.
    - All outgoing transmission requests are recorded in a local test file:
      outputs/simulated_outbound_transmissions.log
    - Requires caller authorization and verified human-in-the-loop approval.
    """

    def __init__(self, log_path: str = "outputs/simulated_outbound_transmissions.log", audit_logger: Optional[AuditLogger] = None):
        self.log_path = log_path
        os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
        self.audit_logger = audit_logger

    def transmit(self, destination: str, payload: str, protocol: str = "webhook", approval_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes simulated transmission ONLY after authorization and recording in local isolation.
        """
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "timestamp": now,
            "protocol": protocol,
            "destination": destination,
            "payload_preview": SecretScanner.redact(payload[:200]),
            "payload_length": len(payload),
            "approval_token": approval_token,
            "simulated": True
        }

        # Write to local quarantine simulation log
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            return {"success": False, "error": f"Failed to record simulated transmission: {str(e)}"}

        if self.audit_logger:
            self.audit_logger.log(
                event_type="OUTBOUND_TRANSMISSION_SIMULATED",
                actor="SimulatedOutboundTool",
                action="transmit",
                details={
                    "destination": destination,
                    "protocol": protocol,
                    "local_quarantine_log": self.log_path
                },
                risk_level="MEDIUM",
                status="ALLOWED"
            )

        return {
            "success": True,
            "message": f"Simulated {protocol} outbound payload captured in local quarantine log: {self.log_path}",
            "record": record
        }


class ToolDispatcher:
    """
    Central Tool-Call Validation and Least-Privilege Gate.
    Restricts access to tools based on role assignments, validates call schemas,
    and intercepts unauthorized or suspicious tool requests.
    """

    ROLE_PERMISSIONS: Dict[str, List[ToolPermission]] = {
        "security_analyst": [ToolPermission.READ_ONLY, ToolPermission.STATIC_ANALYSIS, ToolPermission.REPORT_GENERATION],
        "read_only_viewer": [ToolPermission.READ_ONLY],
        "dispatch_officer": [ToolPermission.READ_ONLY, ToolPermission.OUTBOUND_DISPATCH],
        "untrusted_code_executor": []  # Zero permissions
    }

    TOOL_REQUIRED_PERMISSIONS: Dict[str, ToolPermission] = {
        "SecretScanner": ToolPermission.STATIC_ANALYSIS,
        "ASTVulnerabilityScanner": ToolPermission.STATIC_ANALYSIS,
        "ReportGenerator": ToolPermission.REPORT_GENERATION,
        "SimulatedOutboundTool": ToolPermission.OUTBOUND_DISPATCH
    }

    def __init__(self, outbound_tool: SimulatedOutboundTool, audit_logger: Optional[AuditLogger] = None):
        self.outbound_tool = outbound_tool
        self.audit_logger = audit_logger

    def validate_and_execute(self, request: ToolCallRequest, approval_verified: bool = False) -> ToolCallResult:
        """
        Validates the tool call against:
        1. Tool registration
        2. Role-Based Access Control / Least Privilege
        3. Parameter constraints
        4. Human approval requirement for outbound dispatch
        """
        tool_name = request.tool_name
        caller_role = request.caller_role

        # 1. Existence check
        if tool_name not in self.TOOL_REQUIRED_PERMISSIONS:
            err = f"Tool-call validation failed: Tool '{tool_name}' is not registered or authorized."
            self._log_tool_rejection(request, "UNREGISTERED_TOOL", err)
            return ToolCallResult(call_id=request.call_id, tool_name=tool_name, success=False, blocked_by="ToolDispatcher", error_message=err)

        required_perm = self.TOOL_REQUIRED_PERMISSIONS[tool_name]
        granted_perms = self.ROLE_PERMISSIONS.get(caller_role, [])

        # 2. Least Privilege / RBAC validation
        if required_perm not in granted_perms:
            err = (
                f"Least Privilege violation: Caller role '{caller_role}' lacks required permission "
                f"'{required_perm.value}' to invoke tool '{tool_name}'."
            )
            self._log_tool_rejection(request, "INSUFFICIENT_PERMISSIONS", err)
            return ToolCallResult(call_id=request.call_id, tool_name=tool_name, success=False, blocked_by="LeastPrivilegeEnforcer", error_message=err)

        # 3. Mandatory Human Approval gate for outbound transmissions
        if tool_name == "SimulatedOutboundTool":
            if not approval_verified:
                err = "Tool-call blocked: Human approval gate required for simulated outbound transmission. Explicit approval token missing or rejected."
                self._log_tool_rejection(request, "HUMAN_APPROVAL_REQUIRED", err)
                return ToolCallResult(call_id=request.call_id, tool_name=tool_name, success=False, blocked_by="ApprovalManager", error_message=err)

            # Execute outbound simulation
            dest = request.parameters.get("destination", "")
            payload = request.parameters.get("payload", "")
            proto = request.parameters.get("protocol", "webhook")
            token = request.auth_token

            res = self.outbound_tool.transmit(dest, payload, proto, approval_token=token)
            return ToolCallResult(call_id=request.call_id, tool_name=tool_name, success=res["success"], output=res)

        # Other static analysis tools are handled directly by the agent
        return ToolCallResult(call_id=request.call_id, tool_name=tool_name, success=True, output="Authorized")

    def _log_tool_rejection(self, request: ToolCallRequest, reason: str, error_msg: str):
        if self.audit_logger:
            self.audit_logger.log(
                event_type="TOOL_CALL_REJECTED",
                actor="ToolDispatcher",
                action=f"invoke_{request.tool_name}",
                details={
                    "call_id": request.call_id,
                    "caller_role": request.caller_role,
                    "tool": request.tool_name,
                    "violation": reason,
                    "error": error_msg
                },
                risk_level="HIGH",
                status="BLOCKED"
            )

