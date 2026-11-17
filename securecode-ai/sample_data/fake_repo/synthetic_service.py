"""
synthetic_service.py
--------------------
Clean, production-grade microservice component following secure coding best practices.
Demonstrates clean baseline execution where no vulnerabilities or injections are present.
"""

import os
import hashlib
import json
from typing import Dict, Any, Optional


class CleanPaymentService:
    """Handles payment verification safely using environment variables and parameterized interfaces."""

    def __init__(self):
        # Reads configuration safely from environment variables (no hardcoded secrets)
        self.api_endpoint = os.getenv("PAYMENT_GATEWAY_URL", "https://api.secure-gateway.internal/v1")
        self._api_key = os.getenv("PAYMENT_API_KEY", "")

    def generate_idempotency_token(self, order_id: str, timestamp_str: str) -> str:
        """Uses secure SHA-256 hash algorithm for idempotency token generation."""
        payload = f"{order_id}:{timestamp_str}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def sanitize_user_input(self, raw_input: str) -> str:
        """Performs strict boundary checks on transaction memo strings."""
        if not raw_input or len(raw_input) > 256:
            raise ValueError("Invalid transaction memo length.")
        return raw_input.strip()

    def process_transaction(self, order_id: str, amount_cents: int, memo: str) -> Dict[str, Any]:
        """Processes transaction without dangerous dynamic evaluations or shell calls."""
        if amount_cents <= 0:
            return {"status": "FAILED", "reason": "Non-positive amount"}

        clean_memo = self.sanitize_user_input(memo)
        token = self.generate_idempotency_token(order_id, "2026-10-30T10:00:00Z")

        return {
            "status": "APPROVED",
            "order_id": order_id,
            "idempotency_token": token,
            "processed_amount": amount_cents,
            "memo": clean_memo
        }

