"""
input_validator.py
------------------
Input Validation and Boundary Enforcement Layer for SecureCode AI.
Prevents Denial of Service (DoS), memory exhaustion, binary file injection,
directory traversal, and syntax exploitation before processing source files.
"""

import ast
import os
from typing import Tuple, Optional
from audit_logger import AuditLogger


class InputValidationError(Exception):
    """Custom exception raised when source input violates validation constraints."""
    pass


class InputValidator:
    """
    Validates source code inputs against strict operational thresholds:
    - Maximum file size (512 KB limit to prevent resource exhaustion)
    - Encoding integrity (Strict UTF-8 validation, binary detection)
    - Maximum line length and line count (prevents quadratic parsing hazards)
    - Directory boundary enforcement (prevents path traversal)
    - Python syntax verification via abstract syntax tree parsing
    """

    MAX_FILE_SIZE_BYTES = 512 * 1024  # 512 KB
    MAX_LINE_COUNT = 5000
    MAX_LINE_LENGTH = 2000

    def __init__(self, audit_logger: Optional[AuditLogger] = None, allowed_base_dir: Optional[str] = None):
        self.audit_logger = audit_logger
        self.allowed_base_dir = os.path.abspath(allowed_base_dir) if allowed_base_dir else None

    def validate_filepath(self, filepath: str) -> str:
        """
        Validates that a filepath is normalized, safe from directory traversal,
        and located within the allowed base directory.
        """
        abs_path = os.path.abspath(filepath)
        if self.allowed_base_dir:
            common = os.path.commonpath([abs_path, self.allowed_base_dir])
            if common != self.allowed_base_dir:
                msg = f"Path traversal attempt blocked: '{filepath}' lies outside allowed base directory '{self.allowed_base_dir}'"
                if self.audit_logger:
                    self.audit_logger.log(
                        event_type="INPUT_VALIDATION_ERROR",
                        actor="InputValidator",
                        action="validate_filepath",
                        details={"filepath": filepath, "violation": "PATH_TRAVERSAL"},
                        risk_level="HIGH",
                        status="BLOCKED"
                    )
                raise InputValidationError(msg)

        if not os.path.exists(abs_path):
            msg = f"Input file not found: {abs_path}"
            raise InputValidationError(msg)

        if not os.path.isfile(abs_path):
            msg = f"Target path is not a regular file: {abs_path}"
            raise InputValidationError(msg)

        return abs_path

    def validate_content(self, content_str: str, source_label: str = "inline_code") -> Tuple[bool, Optional[str], Optional[ast.AST]]:
        """
        Validates raw source code string against size, encoding, line length, and AST syntax constraints.
        Returns: (is_valid: bool, error_message: Optional[str], ast_tree: Optional[ast.AST])
        """
        byte_data = content_str.encode("utf-8")
        byte_size = len(byte_data)

        # 1. Size constraint
        if byte_size > self.MAX_FILE_SIZE_BYTES:
            err = f"Input rejected: Payload size ({byte_size} bytes) exceeds limit ({self.MAX_FILE_SIZE_BYTES} bytes)"
            self._log_rejection(source_label, "OVERSIZED_INPUT", err)
            return False, err, None

        # 2. Binary / Null byte check
        if "\x00" in content_str:
            err = "Input rejected: Binary content or null bytes detected in source code stream"
            self._log_rejection(source_label, "BINARY_DATA_DETECTED", err)
            return False, err, None

        # 3. Line count and length checks
        lines = content_str.splitlines()
        if len(lines) > self.MAX_LINE_COUNT:
            err = f"Input rejected: Source contains {len(lines)} lines, exceeding maximum limit ({self.MAX_LINE_COUNT})"
            self._log_rejection(source_label, "EXCESSIVE_LINES", err)
            return False, err, None

        for idx, line in enumerate(lines, start=1):
            if len(line) > self.MAX_LINE_LENGTH:
                err = f"Input rejected: Line {idx} length ({len(line)} chars) exceeds maximum allowed ({self.MAX_LINE_LENGTH})"
                self._log_rejection(source_label, "EXCESSIVE_LINE_LENGTH", err)
                return False, err, None

        # 4. AST Syntax validation
        try:
            tree = ast.parse(content_str, filename=source_label)
        except SyntaxError as syn_err:
            err = f"Input rejected: Malformed Python syntax at line {syn_err.lineno}, col {syn_err.offset}: {syn_err.msg}"
            self._log_rejection(source_label, "SYNTAX_PARSE_ERROR", err)
            return False, err, None
        except Exception as e:
            err = f"Input rejected: Failed to parse Python AST: {str(e)}"
            self._log_rejection(source_label, "AST_EXCEPTION", err)
            return False, err, None

        # Passed validation
        if self.audit_logger:
            self.audit_logger.log(
                event_type="INPUT_VALIDATION_SUCCESS",
                actor="InputValidator",
                action="validate_content",
                details={
                    "source": source_label,
                    "byte_size": byte_size,
                    "line_count": len(lines),
                    "syntax_valid": True
                },
                risk_level="INFO",
                status="ALLOWED"
            )

        return True, None, tree

    def validate_file(self, filepath: str) -> Tuple[bool, Optional[str], Optional[str], Optional[ast.AST]]:
        """
        Validates file existence, size, reads content, and performs content validation.
        Returns: (is_valid: bool, error_message: Optional[str], content: Optional[str], ast_tree: Optional[ast.AST])
        """
        try:
            safe_path = self.validate_filepath(filepath)
        except InputValidationError as e:
            return False, str(e), None, None

        size = os.path.getsize(safe_path)
        if size > self.MAX_FILE_SIZE_BYTES:
            err = f"File '{filepath}' rejected: Size ({size} bytes) exceeds limit ({self.MAX_FILE_SIZE_BYTES} bytes)"
            self._log_rejection(filepath, "OVERSIZED_FILE", err)
            return False, err, None, None

        try:
            with open(safe_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            err = f"File '{filepath}' rejected: Non-UTF8 encoding or binary characters detected"
            self._log_rejection(filepath, "INVALID_ENCODING", err)
            return False, err, None, None
        except Exception as e:
            err = f"File '{filepath}' read error: {str(e)}"
            self._log_rejection(filepath, "IO_ERROR", err)
            return False, err, None, None

        is_valid, err, tree = self.validate_content(content, source_label=os.path.basename(filepath))
        return is_valid, err, content, tree

    def _log_rejection(self, source: str, reason_code: str, message: str):
        if self.audit_logger:
            self.audit_logger.log(
                event_type="INPUT_VALIDATION_REJECTION",
                actor="InputValidator",
                action="validate",
                details={"source": source, "reason_code": reason_code, "error": message},
                risk_level="MEDIUM",
                status="BLOCKED"
            )

