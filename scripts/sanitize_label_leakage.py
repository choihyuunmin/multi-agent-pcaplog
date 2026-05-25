"""Remove direct CIC-IDS2017 label strings from generated benchmark inputs.

This is a deterministic cleanup step for reviewer-response experiments. It
rewrites only model-visible text fields: synthetic syslog lines and QCA
questions/answer reasons. The original ``ground_truth_label`` field is kept for
evaluation bookkeeping.
"""

import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SYSLOG_PATH = os.path.join(ROOT, "data", "CIC-IDS2017", "syslog_threats.log")
DATASET_PATH = os.path.join(ROOT, "results", "qca_test_dataset_100.json")

REPLACEMENTS = [
    (r"\bFTP-Patator\b", "FTP credential guessing"),
    (r"\bSSH-Patator\b", "SSH credential guessing"),
    (r"\bDoS\s+Hulk\b", "HTTP GET flood"),
    (r"\bDoS\s+GoldenEye\b", "HTTP request flood"),
    (r"\bDoS\s+Slowhttptest\b", "slow HTTP request exhaustion"),
    (r"\bDoS\s+slowloris\b", "slow HTTP connection exhaustion"),
    (r"\bSlowloris\b", "slow HTTP connection exhaustion"),
    (r"\bHeartbleed\b", "TLS heartbeat anomaly"),
    (r"\bWeb Attack\s*[–-]?\s*Brute Force\b", "web login brute force"),
    (r"\bWeb Attack\s*[–-]?\s*XSS\b", "web script injection attempt"),
    (r"\bWeb Attack\s*[–-]?\s*Sql Injection\b", "web database injection attempt"),
    (r"\bPortScan\b", "port scan"),
    (r"\bPortscan\b", "port scan"),
    (r"\bDDoS\b", "distributed flood"),
    (r"\bDDOS\b", "distributed flood"),
    (r"\bBENIGN\b", "routine activity"),
    (r"\bbotnet\b", "command-and-control"),
    (r"\bBot\b", "command-and-control activity"),
    (r"\bInfiltration\b", "unauthorized internal activity"),
]


def sanitize_text(text: str) -> str:
    out = text
    for pattern, replacement in REPLACEMENTS:
        out = re.sub(pattern, replacement, out, flags=re.IGNORECASE)
    return out


def sanitize_syslog() -> int:
    if not os.path.exists(SYSLOG_PATH):
        return 0
    with open(SYSLOG_PATH, "r", encoding="utf-8") as f:
        before = f.read()
    after = sanitize_text(before)
    if after != before:
        with open(SYSLOG_PATH, "w", encoding="utf-8") as f:
            f.write(after)
    return before != after


def sanitize_dataset() -> int:
    if not os.path.exists(DATASET_PATH):
        return 0
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    changed = 0
    for case in data:
        for key in ("question",):
            if key in case:
                new_value = sanitize_text(case[key])
                changed += int(new_value != case[key])
                case[key] = new_value
        answer = case.get("expected_answer")
        if isinstance(answer, dict):
            for key in ("reason",):
                if key in answer:
                    new_value = sanitize_text(answer[key])
                    changed += int(new_value != answer[key])
                    answer[key] = new_value

    if changed:
        with open(DATASET_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    return changed


def main():
    syslog_changed = sanitize_syslog()
    dataset_changed = sanitize_dataset()
    print(f"syslog_changed={syslog_changed}")
    print(f"dataset_fields_changed={dataset_changed}")


if __name__ == "__main__":
    main()
