import os
import sys

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
from src.tools import run_tshark, grep_system_logs, apply_snort_rules


def setup_test_data():
    """테스트용 더미 데이터 생성."""
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "CIC-IDS2017")
    os.makedirs(data_dir, exist_ok=True)

    csv_path = os.path.join(data_dir, "Tuesday-WorkingHours.pcap_ISCX.csv")
    if not os.path.exists(csv_path):
        pd.DataFrame({
            "Source IP": ["192.168.10.50", "192.168.10.51", "192.168.10.50"],
            "Destination IP": ["172.16.0.1", "172.16.0.1", "172.16.0.1"],
            "Label": ["FTP-Patator", "BENIGN", "FTP-Patator"],
        }).to_csv(csv_path, index=False)

    pcap_path = os.path.join(data_dir, "Tuesday-WorkingHours.pcap")
    if not os.path.exists(pcap_path):
        with open(pcap_path, "w") as f:
            f.write("")


def test_tools():
    setup_test_data()
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    data_dir = os.path.join(root, "data", "CIC-IDS2017")
    csv_path = os.path.join(data_dir, "Tuesday-WorkingHours.pcap_ISCX.csv")
    pcap_path = os.path.join(data_dir, "Tuesday-WorkingHours.pcap")

    print("\n" + "=" * 50)
    print("TOOLS UNIT TEST (Collaborative Multi-Agent)")
    print("=" * 50)

    print("\n[1] grep_system_logs (논문: direct analysis on system logs)")
    grep_res = grep_system_logs("192.168.10.50", csv_path)
    print(f"    Snippet: {str(grep_res)[:120]}...")
    assert "192.168.10.50" in grep_res

    print("\n[2] apply_snort_rules (Baseline: centralized rule-set)")
    df = pd.read_csv(csv_path)
    alerts = apply_snort_rules(df)
    print(f"    Alerts found: {len(alerts)}")
    assert alerts
    assert any("FTP" in alert["rule"] for alert in alerts)

    print("\n[3] run_tshark (논문: tool-based analysis on raw packets)")
    tshark_res = run_tshark("ip.addr == 192.168.10.50", pcap_path)
    print(f"    Result: {str(tshark_res)[:120]}...")
    assert isinstance(tshark_res, str)

    print("\n" + "=" * 50)
    print("TOOLS UNIT TEST COMPLETE")
    print("=" * 50)


if __name__ == "__main__":
    test_tools()
