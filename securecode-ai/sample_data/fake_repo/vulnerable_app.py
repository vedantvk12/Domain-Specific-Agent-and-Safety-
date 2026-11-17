"""
vulnerable_app.py
-----------------
Synthetic vulnerable application containing intentional, simulated security defects
for testing SecureCode AI detection capabilities.
Contains fake API credentials, unsafe dynamic functions, command injection sinks,
and unmasked sensitive data logging.
"""

import os
import hashlib
import sqlite3

# [FAKE DATA] Hardcoded dummy cloud credentials for security benchmark testing
AWS_ACCESS_KEY_ID = "AKIAFAKE1234567890EX"
AWS_SECRET_ACCESS_KEY = "dummy_secret_key_9876543210_not_real"
STRIPE_SECRET_KEY = "sk_live_fake9876543210abcdef12345678"
DATABASE_URL = "postgres://admin_user:SuperSecretTestPass123!@db.internal:5432/finance_db"


def calculate_dynamic_expression(user_formula: str):
    """VULNERABILITY: Arbitrary code execution via eval()"""
    print(f"Executing mathematical formula: {user_formula}")
    result = eval(user_formula)  # CWE-95: Dangerous dynamic evaluation
    return result


def backup_system_logs(archive_name: str):
    """VULNERABILITY: Command injection sink via os.system()"""
    command = f"tar -czf {archive_name}.tar.gz /var/log/app.log"
    os.system(command)  # CWE-78: Unsanitized shell command execution


def lookup_customer_record(cursor, account_id: str):
    """VULNERABILITY: SQL injection via string formatting"""
    query = f"SELECT * FROM customer_accounts WHERE id = '{account_id}'"  # CWE-89
    cursor.execute(query)
    return cursor.fetchall()


def compute_legacy_checksum(data: str) -> str:
    """VULNERABILITY: Weak hash algorithm MD5"""
    return hashlib.md5(data.encode()).hexdigest()  # CWE-328


def authenticate_user(username: str, password_hash: str):
    """VULNERABILITY: Sensitive data exposure to standard output"""
    print(f"DEBUG: Authenticating user='{username}' with stripe_key='{STRIPE_SECRET_KEY}'")  # CWE-532
    return True

