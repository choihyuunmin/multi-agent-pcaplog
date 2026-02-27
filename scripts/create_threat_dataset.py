import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
import json
import asyncio
import glob
from src.agents import LLMProvider

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(ROOT, "data", "CIC-IDS2017")
RESULTS_DIR = os.path.join(ROOT, "results")
SYSLOG_PATH = os.path.join(DATA_DIR, "syslog_threats.log")
DATASET_PATH = os.path.join(RESULTS_DIR, "qca_test_dataset_100.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)


async def create_threat_dataset():
    csv_files = glob.glob(os.path.join(ROOT, "data", "*.pcap_ISCX.csv"))
    llm = LLMProvider(backend="auto", model="gpt-5")

    malicious_pool = []
    benign_pool = []

    for f in csv_files:
        try:
            df = pd.read_csv(f, encoding="cp1252", low_memory=False)
            df.columns = [c.strip() for c in df.columns]
            df = df.dropna(subset=["Label", "Source IP", "Destination IP"])

            mal = df[df["Label"] != "BENIGN"]
            ben = df[df["Label"] == "BENIGN"]

            malicious_pool.append(mal)
            benign_pool.append(ben)
            print(f"Loaded {f}: Malicious={len(mal)}, Benign={len(ben)}")
        except Exception as e:
            print(f"Error reading {f}: {e}")

    if not malicious_pool:
        print("No malicious data found.")
        return

    all_malicious = pd.concat(malicious_pool).sample(min(60, len(pd.concat(malicious_pool))))
    all_benign = pd.concat(benign_pool).sample(min(40, len(pd.concat(benign_pool))))
    final_df = pd.concat([all_malicious, all_benign]).sample(frac=1).reset_index(drop=True)

    # 위협 데이터를 OpenAI에 넘겨 자유 형식 syslog 생성 (틀 없이)
    syslog_per_row = []  # row index -> [syslog lines]
    qca_dataset = []
    total = len(final_df)
    rows_list = list(final_df.iterrows())

    print(f"Step 1: Passing threat data to OpenAI — generating free-form syslog (no template)...")
    for i, (_, row) in enumerate(rows_list):
        label = row["Label"]
        src_ip = row["Source IP"]
        dst_ip = row["Destination IP"]
        dest_port = int(row["Destination Port"]) if pd.notna(row["Destination Port"]) else 0
        duration = float(row["Flow Duration"]) if pd.notna(row["Flow Duration"]) else 0
        fwd_pkts = int(row["Total Fwd Packets"]) if pd.notna(row["Total Fwd Packets"]) else 0
        bwd_pkts = int(row["Total Backward Packets"]) if pd.notna(row["Total Backward Packets"]) else 0

        threat_context = {
            "source_ip": src_ip,
            "destination_ip": dst_ip,
            "destination_port": dest_port,
            "flow_duration_sec": duration,
            "fwd_packets": fwd_pkts,
            "bwd_packets": bwd_pkts,
            "attack_type": label,
            "timestamp": str(row["Timestamp"]) if pd.notna(row.get("Timestamp")) else "",
        }

        prompt = f"""You are a security analyst. Below is network flow data from an IDS that detected potential traffic.

Threat/Flow context:
{json.dumps(threat_context, indent=2)}

Write 1-2 lines of realistic Linux syslog that would be logged when this activity occurs. 
- For attacks (non-BENIGN): describe the threat naturally — failed logins, connection floods, port scans, infiltration, etc. Write however a real system would log it.
- For BENIGN: write normal operation logs — successful connections, routine traffic.
- Include the source IP ({src_ip}) in the log so we can correlate.
- No fixed format. Write naturally as a Linux daemon/kernel would.
Output ONLY the syslog line(s). No explanation, no markdown."""

        try:
            res = await llm.call_performance_model(prompt, model_name="gpt-5")
            log_text = (res.get("text") or "").strip().strip('"\'')
            lines = [ln.strip() for ln in log_text.split("\n") if ln.strip()]
            if not lines or src_ip not in " ".join(lines):
                lines = [f"[{label}] Suspicious activity from {src_ip} to {dst_ip}:{dest_port}"]
            syslog_per_row.append(lines)
            print(f"  [{i+1}/{total}] {label} ({src_ip}) → {lines[0][:70]}...")
        except Exception as e:
            print(f"  Syslog gen failed for {src_ip}: {e}")
            syslog_per_row.append([f"[{label}] Activity from {src_ip}"])

    syslog_lines = []
    for lines in syslog_per_row:
        syslog_lines.extend(lines)

    with open(SYSLOG_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(syslog_lines))
    print(f"Saved syslog: {SYSLOG_PATH} ({len(syslog_lines)} lines)")

    print(f"Step 2: Creating test dataset from generated syslog + flow data...")
    for i, (_, row) in enumerate(rows_list):
        label = row["Label"]
        src_ip = row["Source IP"]
        dst_ip = row["Destination IP"]
        generated_syslog = "\n".join(syslog_per_row[i] if i < len(syslog_per_row) else [])

        context = {
            "flow_id": f"{src_ip}-{dst_ip}",
            "protocol": int(row["Protocol"]) if pd.notna(row["Protocol"]) else 6,
            "duration": float(row["Flow Duration"]) if pd.notna(row["Flow Duration"]) else 0,
            "total_fwd_pkts": int(row["Total Fwd Packets"]) if pd.notna(row["Total Fwd Packets"]) else 0,
            "total_bwd_pkts": int(row["Total Backward Packets"]) if pd.notna(row["Total Backward Packets"]) else 0,
            "dest_port": int(row["Destination Port"]) if pd.notna(row["Destination Port"]) else 0,
            "timestamp": str(row["Timestamp"]),
        }

        prompt = f"""You have this real syslog and network flow data (from IDS):

Syslog:
{generated_syslog}

Flow: {json.dumps(context)}

Ground truth: {label} (Malicious if not BENIGN, else Benign).

Create a test case for an attack detection system:
1) One investigation question (natural language) that asks whether this activity is malicious and what kind of attack.
2) The correct answer: verdict (Malicious or Benign) and brief reason.

Output JSON only: {{"question": "...", "answer": {{"verdict": "Malicious" or "Benign", "reason": "..."}}}}"""

        try:
            res = await llm.call_performance_model(prompt, model_name="gpt-5")
            text = res.get("text", "")
            start = text.find("{")
            end = text.rfind("}") + 1
            qca_json = json.loads(text[start:end])

            qca_dataset.append({
                "id": i + 1,
                "question": qca_json.get("question", f"Does activity from {src_ip} indicate an attack?"),
                "context": context,
                "expected_answer": qca_json.get("answer", {"verdict": "Malicious" if label != "BENIGN" else "Benign", "reason": str(label)}),
                "ground_truth_label": label,
                "target_ip": src_ip,
            })
        except Exception:
            qca_dataset.append({
                "id": i + 1,
                "question": f"Does the syslog and packet data from {src_ip} indicate an attack?",
                "context": context,
                "expected_answer": {"verdict": "Malicious" if label != "BENIGN" else "Benign", "reason": str(label)},
                "ground_truth_label": label,
                "target_ip": src_ip,
            })
        print(f"[{i+1}/{total}] QCA for {label} ({src_ip})")

    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(qca_dataset, f, indent=4, ensure_ascii=False)
    print(f"Success: {DATASET_PATH} ({len(qca_dataset)} samples)")
    print(f"Syslog used: {SYSLOG_PATH}")


if __name__ == "__main__":
    asyncio.run(create_threat_dataset())
