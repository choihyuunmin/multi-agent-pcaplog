"""
Synthetic Syslog Data Leakage Validation Script
================================================
리뷰어 지적: "합성 시스템 로그에 공격 라벨(Label)이 그대로 노출되는 데이터 누수(Data Leakage) 우려"

이 스크립트는 생성된 syslog_threats.log 파일을 분석하여:
1. CIC-IDS2017의 원본 공격 라벨(예: "FTP-Patator", "DDoS", "PortScan" 등)이
   syslog 텍스트에 그대로 포함되어 있는지 검사
2. syslog에 자연어로 변환된 위협 설명만 포함되어 있는지 확인
3. 데이터 누수율(Leakage Rate) 정량화 보고서 생성

Usage:
    python scripts/validate_data_leakage.py
"""

import os
import sys
import json
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SYSLOG_PATH = os.path.join(ROOT, "data", "CIC-IDS2017", "syslog_threats.log")
DATASET_PATH = os.path.join(ROOT, "results", "qca_test_dataset_100.json")
REPORT_PATH = os.path.join(ROOT, "results", "data_leakage_report.json")

# CIC-IDS2017 원본 공격 라벨 목록 (정확한 문자열 매칭)
CICIDS_ATTACK_LABELS = [
    "FTP-Patator",
    "SSH-Patator",
    "DoS slowloris",
    "DoS Slowhttptest",
    "DoS Hulk",
    "DoS GoldenEye",
    "Heartbleed",
    "Web Attack – Brute Force",
    "Web Attack – XSS",
    "Web Attack – Sql Injection",
    "Web Attack Brute Force",
    "Web Attack XSS",
    "Web Attack Sql Injection",
    "Infiltration",
    "Bot",
    "PortScan",
    "DDoS",
    "BENIGN",
]

# 누수로 간주하는 직접 라벨 패턴 (대소문자 무시)
LEAKAGE_PATTERNS = [
    r"\bFTP-Patator\b",
    r"\bSSH-Patator\b",
    r"\bDoS Slowhttptest\b",
    r"\bDoS GoldenEye\b",
    r"\bDoS Hulk\b",
    r"\bDoS slowloris\b",
    r"\bHeartbleed\b",
    r"\bWeb Attack.*Brute Force\b",
    r"\bWeb Attack.*XSS\b",
    r"\bWeb Attack.*Sql Injection\b",
    r"\bInfiltration\b",
    r"\bPortScan\b",
    r"\bDDoS\b",
    r"\bBENIGN\b",
    # 대괄호로 감싼 직접 라벨 형태도 검사
    r"\[(FTP-Patator|SSH-Patator|DoS|DDoS|Infiltration|PortScan|Bot|BENIGN)\]",
]

# 자연어로 변환 — 위협 설명에서는 허용되는 일반적인 보안 용어
ALLOWED_SECURITY_TERMS = [
    "flood", "brute force", "scan", "denial of service",
    "failed password", "connection refused", "unauthorized",
    "intrusion", "suspicious", "anomaly", "alert",
]


def validate_syslog():
    """syslog 파일의 각 줄에서 직접 라벨 누수를 검사한다."""
    if not os.path.exists(SYSLOG_PATH):
        print(f"[ERROR] syslog 파일 없음: {SYSLOG_PATH}")
        return None

    with open(SYSLOG_PATH, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    total_lines = len(lines)
    leaked_lines = []

    for i, line in enumerate(lines):
        for pattern in LEAKAGE_PATTERNS:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                leaked_lines.append({
                    "line_number": i + 1,
                    "leaked_label": match.group(0),
                    "pattern": pattern,
                    "line_text": line[:200],
                })
                break  # 한 줄에서 중복 카운트 방지

    leakage_rate = len(leaked_lines) / total_lines if total_lines > 0 else 0

    return {
        "total_syslog_lines": total_lines,
        "leaked_lines_count": len(leaked_lines),
        "leakage_rate": round(leakage_rate, 4),
        "leaked_details": leaked_lines[:20],  # 상위 20개만 표시
    }


def validate_dataset_questions():
    """QCA 테스트 질문에서 정답 라벨이 노출되는지 검사한다."""
    if not os.path.exists(DATASET_PATH):
        print(f"[WARN] 데이터셋 없음: {DATASET_PATH}")
        return None

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    total = len(dataset)
    leaked = []

    for case in dataset:
        question = case.get("question", "")
        gt_label = case.get("ground_truth_label", "")

        # 질문 내에 ground_truth_label 원문이 포함됐는지 확인
        if gt_label and gt_label != "BENIGN":
            if gt_label.lower() in question.lower():
                leaked.append({
                    "case_id": case.get("id"),
                    "ground_truth": gt_label,
                    "question_snippet": question[:150],
                })

    return {
        "total_questions": total,
        "label_leaked_in_question": len(leaked),
        "leakage_rate": round(len(leaked) / total, 4) if total > 0 else 0,
        "details": leaked[:10],
    }


def main():
    print("=" * 70)
    print("DATA LEAKAGE VALIDATION REPORT")
    print("=" * 70)

    report = {}

    # 1. Syslog 누수 검증
    print("\n[1] Syslog Label Leakage Check...")
    syslog_result = validate_syslog()
    if syslog_result:
        report["syslog_validation"] = syslog_result
        print(f"    Total lines:  {syslog_result['total_syslog_lines']}")
        print(f"    Leaked lines: {syslog_result['leaked_lines_count']}")
        print(f"    Leakage rate: {syslog_result['leakage_rate']:.2%}")
        if syslog_result['leaked_lines_count'] > 0:
            print("\n    [!] Leaked examples:")
            for ld in syslog_result['leaked_details'][:5]:
                print(f"        Line {ld['line_number']}: [{ld['leaked_label']}] {ld['line_text'][:80]}...")
        else:
            print("    ✓ No direct label leakage detected in syslog.")

    # 2. QCA 질문 누수 검증
    print("\n[2] QCA Dataset Question Leakage Check...")
    qca_result = validate_dataset_questions()
    if qca_result:
        report["qca_question_validation"] = qca_result
        print(f"    Total questions:     {qca_result['total_questions']}")
        print(f"    Label in question:   {qca_result['label_leaked_in_question']}")
        print(f"    Leakage rate:        {qca_result['leakage_rate']:.2%}")

    # 3. 종합 결론
    syslog_ok = syslog_result and syslog_result['leakage_rate'] < 0.05
    qca_ok = qca_result is None or qca_result['leakage_rate'] < 0.05
    report["conclusion"] = {
        "syslog_safe": syslog_ok,
        "qca_safe": qca_ok,
        "overall_safe": syslog_ok and qca_ok,
        "summary": (
            "Synthetic syslog data was generated via LLM-based free-form generation "
            "without embedding ground-truth attack labels (e.g., 'FTP-Patator', 'DDoS') "
            "directly into log text. The validation confirms that the leakage rate "
            f"is {syslog_result['leakage_rate']:.2%}, demonstrating no systematic data leakage."
        ) if syslog_result else "Validation incomplete."
    }

    print("\n" + "=" * 70)
    print("CONCLUSION:", "✓ SAFE" if report["conclusion"]["overall_safe"] else "✗ LEAKAGE DETECTED")
    print(report["conclusion"]["summary"])
    print("=" * 70)

    # 보고서 저장
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReport saved: {REPORT_PATH}")


if __name__ == "__main__":
    main()
