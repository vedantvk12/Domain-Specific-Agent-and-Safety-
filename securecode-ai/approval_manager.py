"""
approval_manager.py
-------------------
Human-in-the-Loop (HITL) Approval Gate for SecureCode AI.
Enforces strict manual or policy verification before any simulated outbound transmission
or high-risk operation can proceed. Blocks covert exfiltration attempts.
"""

import uuid
from typing import Optional, Tuple
from models import ApprovalRequest, ApprovalStatus
from audit_logger import AuditLogger
from security_tools import SecretScanner


class ApprovalManager:
    """
    Manages human authorization workflows for security-sensitive actions.
    Ensures that automated agent logic cannot dispatch data outside local boundaries
    without affirmative human or security policy consent.
    """

    def __init__(self, auto_policy: Optional[str] = None, audit_logger: Optional[AuditLogger] = None):
        """
        auto_policy: 'DENY_ALL' (default safe policy), 'ALLOW_ALL' (for specific positive unit tests),
                     or None (prompts interactive user in console).
        """
        self.auto_policy = auto_policy or "DENY_ALL"
        self.audit_logger = audit_logger

    def request_approval(
        self,
        tool_name: str,
        destination: str,
        payload: str,
        risk_summary: str,
        is_injection_suspected: bool = False
    ) -> Tuple[bool, Optional[str], ApprovalRequest]:
        """
        Submits an approval ticket for human review.
        Returns: (is_approved: bool, approval_token: Optional[str], ticket: ApprovalRequest)
        """
        req_id = f"APV-{uuid.uuid4().hex[:8].upper()}"
        preview = SecretScanner.redact(payload[:250])

        ticket = ApprovalRequest(
            request_id=req_id,
            tool_name=tool_name,
            destination=destination,
            payload_preview=preview,
            risk_summary=risk_summary,
            status=ApprovalStatus.PENDING
        )

        # Immediate denial if prompt injection was already suspected in context
        if is_injection_suspected:
            ticket.status = ApprovalStatus.AUTO_DENIED
            ticket.operator_comment = "AUTOMATIC DENIAL: Outbound transmission requested while active Prompt Injection threat was flagged."
            self._log_decision(ticket, "CRITICAL", "BLOCKED")
            return False, None, ticket

        # Check policy
        if self.auto_policy == "DENY_ALL":
            ticket.status = ApprovalStatus.REJECTED
            ticket.operator_comment = "SECURITY POLICY ENFORCEMENT: Outbound transmissions are denied by default under zero-trust baseline."
            self._log_decision(ticket, "HIGH", "BLOCKED")
            return False, None, ticket

        elif self.auto_policy == "ALLOW_ALL":
            ticket.status = ApprovalStatus.APPROVED
            ticket.operator_comment = "OPERATOR APPROVED: Authorized by test supervisor under controlled lab conditions."
            token = f"AUTH-TOKEN-{uuid.uuid4().hex[:12].upper()}"
            self._log_decision(ticket, "MEDIUM", "APPROVED", token)
            return True, token, ticket

        # Interactive fallback
        print("\n" + "=" * 65)
        print(" [HUMAN APPROVAL REQUIRED] Security Authorization Check")
        print("=" * 65)
        print(f" Request ID  : {ticket.request_id}")
        print(f" Tool Target : {ticket.tool_name}")
        print(f" Destination : {ticket.destination}")
        print(f" Risk Summary: {ticket.risk_summary}")
        print(f" Payload Snippet:\n    {ticket.payload_preview}")
        print("-" * 65)

        try:
            choice = input(" Authorize this transmission? (yes/no): ").strip().lower()
            if choice in ("yes", "y"):
                ticket.status = ApprovalStatus.APPROVED
                ticket.operator_comment = "Manual approval granted by console operator."
                token = f"AUTH-TOKEN-{uuid.uuid4().hex[:12].upper()}"
                self._log_decision(ticket, "INFO", "APPROVED", token)
                return True, token, ticket
            else:
                ticket.status = ApprovalStatus.REJECTED
                ticket.operator_comment = "Explicitly rejected by human operator."
                self._log_decision(ticket, "HIGH", "BLOCKED")
                return False, None, ticket
        except EOFError:
            ticket.status = ApprovalStatus.REJECTED
            ticket.operator_comment = "Non-interactive environment encountered; default denial enforced."
            self._log_decision(ticket, "HIGH", "BLOCKED")
            return False, None, ticket

    def _log_decision(self, ticket: ApprovalRequest, risk_level: str, status: str, token: Optional[str] = None):
        if self.audit_logger:
            self.audit_logger.log(
                event_type="HUMAN_APPROVAL_DECISION",
                actor="ApprovalManager",
                action="review_request",
                details={
                    "request_id": ticket.request_id,
                    "tool": ticket.tool_name,
                    "destination": ticket.destination,
                    "decision": ticket.status.value,
                    "comment": ticket.operator_comment,
                    "token_issued": bool(token)
                },
                risk_level=risk_level,
                status=status
            )

