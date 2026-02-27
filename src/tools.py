import os
import re
import subprocess

from typing import List, Dict, Any, Optional

# Allow only paths under this directory (default: project/data)
_ALLOWED_BASE = os.path.realpath(
    os.environ.get("TOOLS_ALLOWED_BASE") or os.path.join(os.path.dirname(__file__), "..", "data")
)
_MAX_FILTER_LEN = 256
_MAX_PATTERN_LEN = 256
_MAX_OUTPUT_BYTES = 64 * 1024  # 64 KiB
_MAX_SNORT_INPUT_LEN = 1024 * 1024  # 1 MiB
_MAX_SNORT_ALERTS = 100
_TSHARK_TIMEOUT = 15
_GREP_TIMEOUT = 10


def _resolve_allowed_path(path: str, must_be_file: bool = True) -> Optional[str]:
    """Resolve path and ensure it is under _ALLOWED_BASE. Returns None if invalid."""
    if not path or not path.strip():
        return None
    try:
        resolved = os.path.realpath(os.path.abspath(path))
        if not resolved.startswith(_ALLOWED_BASE):
            return None
        if must_be_file and os.path.isdir(resolved):
            return None
        return resolved
    except (OSError, ValueError):
        return None


def _truncate_output(text: str, max_bytes: int = _MAX_OUTPUT_BYTES) -> str:
    if len(text.encode("utf-8")) <= max_bytes:
        return text
    enc = text.encode("utf-8")
    return enc[:max_bytes].decode("utf-8", errors="replace") + "\n[... output truncated ...]"


def run_tshark(display_filter: str, pcap_path: str) -> str:
    if not display_filter or not isinstance(display_filter, str):
        return "Error: display_filter must be a non-empty string."
    display_filter = display_filter.strip()
    if len(display_filter) > _MAX_FILTER_LEN:
        return f"Error: display_filter exceeds maximum length ({_MAX_FILTER_LEN})."

    # Only allow tshark display filter syntax: alphanumeric, dots, spaces, ==, and common operators
    if not re.match(r"^[a-zA-Z0-9._\s=<>!&|()\-]+$", display_filter):
        return "Error: display_filter contains disallowed characters."

    resolved_path = _resolve_allowed_path(pcap_path, must_be_file=True)
    if resolved_path is None:
        return "Error: PCAP path is not allowed or not a file."
    if not os.path.exists(resolved_path):
        return f"Error: PCAP file not found at {pcap_path}"

    cmd = [
        "tshark", "-r", resolved_path,
        "-Y", display_filter,
        "-T", "fields",
        "-e", "frame.time_relative",
        "-e", "ip.src",
        "-e", "ip.dst",
        "-e", "tcp.flags.str",
        "-c", "20",
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=_TSHARK_TIMEOUT,
        )
        out = result.stdout if result.stdout else "No matching packets found."
        if result.stderr and "Error" in result.stderr:
            out += "\n(Warning: " + result.stderr.strip()[:200] + ")"
        return _truncate_output(out)
    except subprocess.TimeoutExpired:
        return "Tshark Execution Error: timeout exceeded."
    except Exception as e:
        return f"Tshark Execution Error: {str(e)}"


def grep_system_logs(pattern: str, file_path: str) -> str:
    if not pattern or not isinstance(pattern, str):
        return "Error: pattern must be a non-empty string."
    pattern = pattern.strip()
    if len(pattern) > _MAX_PATTERN_LEN:
        return f"Error: pattern exceeds maximum length ({_MAX_PATTERN_LEN})."

    # If pattern looks like a literal (IP/hostname), use -F to avoid ReDoS
    is_literal = bool(re.match(r"^[a-zA-Z0-9.:\-_\s]+$", pattern))
    resolved_path = _resolve_allowed_path(file_path, must_be_file=True)
    if resolved_path is None:
        return "Error: log file path is not allowed or not a file."
    if not os.path.exists(resolved_path):
        return "Log file not found."

    try:
        if is_literal:
            cmd = ["grep", "-m", "10", "-F", pattern, resolved_path]
        else:
            cmd = ["grep", "-m", "10", "-E", pattern, resolved_path]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=_GREP_TIMEOUT,
        )
        out = result.stdout if result.stdout else "No matching logs."
        return _truncate_output(out)
    except subprocess.TimeoutExpired:
        return "Grep Error: timeout exceeded."
    except Exception as e:
        return f"Grep Error: {str(e)}"


def apply_snort_rules(data_str: str) -> List[Dict[str, Any]]:
    if not isinstance(data_str, str):
        return []
    if len(data_str) > _MAX_SNORT_INPUT_LEN:
        data_str = data_str[:_MAX_SNORT_INPUT_LEN]

    alerts: List[Dict[str, Any]] = []
    rules = [
        {"pattern": "FTP", "msg": "Potential FTP Brute Force"},
        {"pattern": "SSH", "msg": "Potential SSH Brute Force"},
        {"pattern": "sshd", "msg": "SSH daemon activity"},
        {"pattern": "Failed password", "msg": "Failed login / Brute Force"},
        {"pattern": "DoS", "msg": "DoS Attack Detected"},
        {"pattern": "DDoS", "msg": "DDoS Attack Detected"},
        {"pattern": "Infiltration", "msg": "Infiltration Detected"},
        {"pattern": "Hulk", "msg": "DoS Hulk Detected"},
        {"pattern": "PortScan", "msg": "Port Scan Detected"},
        {"pattern": "flood", "msg": "Connection/Flood attack"},
        {"pattern": "attack", "msg": "Attack indicator"},
    ]
    data_lower = data_str.lower()
    for rule in rules:
        if rule["pattern"].lower() in data_lower:
            alerts.append({"rule": rule["msg"]})
            if len(alerts) >= _MAX_SNORT_ALERTS:
                break
    return alerts
