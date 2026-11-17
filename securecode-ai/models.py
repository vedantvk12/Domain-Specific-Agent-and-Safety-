"""
models.py
---------
Domain-Specific AI Agent Data Models for SecureCode AI.
Defines schemas for security findings, tool requests, human approval gates,
audit logging, and assessment reports using Pydantic.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class VulnerabilityCategory(str, Enum):
    HARDCODED_CREDENTIAL = "HARDCODED_CREDENTIAL"
    SUSPICIOUS_FUNCTION = "SUSPICIOUS_FUNCTION"
    UNSAFE_OPERATION = "UNSAFE_OPERATION"
    DATA_EXPOSURE = "DATA_EXPOSURE"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    INPUT_VALIDATION_FAILURE = "INPUT_VALIDATION_FAILURE"


class SecurityFinding(BaseModel):
    finding_id: str = Field(..., description="Unique finding identifier (e.g. SEC-001)")
    title: str = Field(..., description="Short title of the detected vulnerability")
    category: VulnerabilityCategory = Field(..., description="Vulnerability category")
    risk_level: RiskLevel = Field(..., description="Risk severity tier")
    line_number: Optional[int] = Field(None, description="Source line number where defect was detected")
    code_snippet: str = Field(..., description="Extracted code fragment or comment")
    description: str = Field(..., description="Technical explanation of the security risk")
    recommendation: str = Field(..., description="Actionable remediation guidance")
    cwe_id: Optional[str] = Field(None, description="Common Weakness Enumeration ID (e.g. CWE-798)")


class ToolPermission(str, Enum):
    READ_ONLY = "READ_ONLY"
    STATIC_ANALYSIS = "STATIC_ANALYSIS"
    REPORT_GENERATION = "REPORT_GENERATION"
    OUTBOUND_DISPATCH = "OUTBOUND_DISPATCH"


class ToolCallRequest(BaseModel):
    call_id: str = Field(..., description="Unique tool call execution ID")
    tool_name: str = Field(..., description="Target tool name to invoke")
    caller_role: str = Field(..., description="Role of the agent component invoking the tool")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Arguments passed to the tool")
    auth_token: Optional[str] = Field(None, description="Authorization token for capability validation")
    justification: str = Field(..., description="Audit justification for why this tool is required")


class ToolCallResult(BaseModel):
    call_id: str = Field(..., description="Matching call ID")
    tool_name: str = Field(..., description="Invoked tool name")
    success: bool = Field(..., description="Whether tool execution succeeded")
    output: Any = Field(default=None, description="Output payload from tool")
    blocked_by: Optional[str] = Field(None, description="Security control that blocked execution if failed")
    error_message: Optional[str] = Field(None, description="Error or reason for rejection")


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    AUTO_DENIED = "AUTO_DENIED"


class ApprovalRequest(BaseModel):
    request_id: str = Field(..., description="Unique approval request ticket")
    tool_name: str = Field(..., description="Tool name requiring human-in-the-loop authorization")
    destination: str = Field(..., description="Destination target (e.g. webhook URL, recipient email)")
    payload_preview: str = Field(..., description="Sanitized preview of proposed outbound payload")
    risk_summary: str = Field(..., description="Summary of risks associated with transmission")
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING, description="Current decision state")
    operator_comment: Optional[str] = Field(None, description="Audit note from human operator or security policy")


class SecurityAssessmentReport(BaseModel):
    target_file: str = Field(..., description="Filename or path analyzed")
    scan_timestamp: str = Field(..., description="ISO 8601 timestamp of analysis")
    status: str = Field(..., description="Status summary (e.g., COMPLETED, BLOCKED)")
    total_findings: int = Field(default=0, description="Total detected security issues")
    critical_count: int = Field(default=0, description="Count of CRITICAL findings")
    high_count: int = Field(default=0, description="Count of HIGH findings")
    medium_count: int = Field(default=0, description="Count of MEDIUM findings")
    low_count: int = Field(default=0, description="Count of LOW findings")
    findings: List[SecurityFinding] = Field(default_factory=list, description="Detailed list of findings")
    summary: str = Field(..., description="Executive narrative summary")
    redaction_applied: bool = Field(default=False, description="True if credentials were redacted")
    injection_threat_neutralized: bool = Field(default=False, description="True if prompt injection was thwarted")


class AuditLogEntry(BaseModel):
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    event_id: str = Field(..., description="Unique event identifier")
    event_type: str = Field(..., description="Security event category")
    actor: str = Field(..., description="Component or identity taking action")
    action: str = Field(..., description="Specific action attempted or executed")
    details: Dict[str, Any] = Field(default_factory=dict, description="Structured contextual metadata")
    risk_level: str = Field(default="INFO", description="Severity or impact tier")
    status: str = Field(..., description="Outcome: ALLOWED, BLOCKED, FLAGGED, REDACTED, ERROR")

