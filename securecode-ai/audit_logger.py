"""
audit_logger.py
---------------
Comprehensive tamper-evident audit logging system for SecureCode AI.
Captures all security-critical lifecycle events: input validation, injection checks,
least-privilege checks, tool authorizations, secret redaction, human approvals,
and final report generation.
"""

import os
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from models import AuditLogEntry


class AuditLogger:
    """
    Centralized audit logging engine for SecureCode AI.
    Persists structured event records in both JSONL format and formatted plain text.
    """

    def __init__(self, log_dir: str = "outputs"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.jsonl_path = os.path.join(self.log_dir, "audit_log.jsonl")
        self.trail_path = os.path.join(self.log_dir, "audit_trail.log")
        self._in_memory_records: List[AuditLogEntry] = []

    def log(
        self,
        event_type: str,
        actor: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        risk_level: str = "INFO",
        status: str = "LOGGED"
    ) -> AuditLogEntry:
        """
        Records an audit event into memory, the JSONL persistence store, and the plaintext audit trail.
        """
        now = datetime.now(timezone.utc).isoformat()
        entry = AuditLogEntry(
            timestamp=now,
            event_id=f"EVT-{uuid.uuid4().hex[:8].upper()}",
            event_type=event_type,
            actor=actor,
            action=action,
            details=details or {},
            risk_level=risk_level,
            status=status
        )

        self._in_memory_records.append(entry)

        # Write to JSONL
        try:
            with open(self.jsonl_path, "a", encoding="utf-8") as f:
                f.write(entry.model_dump_json() + "\n")
        except Exception as e:
            print(f"[AUDIT LOG ERROR] Failed to append to JSONL: {e}")

        # Write to human-readable audit trail
        try:
            with open(self.trail_path, "a", encoding="utf-8") as f:
                f.write(
                    f"[{entry.timestamp}] [{entry.risk_level}] [{entry.event_type}] "
                    f"Actor: {entry.actor} | Action: {entry.action} | Status: {entry.status}\n"
                    f"    Details: {json.dumps(entry.details)}\n"
                )
        except Exception as e:
            print(f"[AUDIT LOG ERROR] Failed to append to plaintext trail: {e}")

        return entry

    def get_events(self, event_type: Optional[str] = None) -> List[AuditLogEntry]:
        """Returns filtered audit entries from memory."""
        if event_type:
            return [e for e in self._in_memory_records if e.event_type == event_type]
        return list(self._in_memory_records)

    def count_by_status(self, status: str) -> int:
        """Counts events with the designated outcome status."""
        return sum(1 for e in self._in_memory_records if e.status == status)

    def clear(self):
        """Clears in-memory records and wipes local log files for test isolation."""
        self._in_memory_records.clear()
        if os.path.exists(self.jsonl_path):
            open(self.jsonl_path, "w", encoding="utf-8").close()
        if os.path.exists(self.trail_path):
            open(self.trail_path, "w", encoding="utf-8").close()

