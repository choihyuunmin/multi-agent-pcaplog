import os
import sys
import asyncio
import json
import time

from typing import Optional

import pandas as pd

from src.agents import MasterOrchestrator, LocalSecurityAgent, LLMProvider
from src.protocol import TaskType
from src.bus import shared_bus
from src.tools import run_tshark, grep_system_logs, apply_snort_rules

DATASET_PATH = "results/qca_test_dataset_100.json"
RESULTS_DIR = "results"
PCAP_PATH = "./data/CIC-IDS2017/Tuesday-WorkingHours.pcap"
LOG_PATH_DEFAULT = "./data/CIC-IDS2017/Tuesday-WorkingHours_converted.csv"
SYSLOG_PATH = "./data/CIC-IDS2017/syslog_threats.log"
LOG_PATH = SYSLOG_PATH if os.path.exists(SYSLOG_PATH) else LOG_PATH_DEFAULT
os.makedirs(RESULTS_DIR, exist_ok=True)

MAS_LLM_BACKEND = os.getenv("MAS_LLM_BACKEND", "ollama")
MAS_LLM_MODEL   = os.getenv("MAS_LLM_MODEL",   "Llama-PcapLog-tool:latest")

# 비교 대상 SA 모델 목록
LLM_CONFIGS = []


def _model_label(backend: str, model: Optional[str]) -> str:
    if model:
        return model.split(":")[0] if ":" in model else model
    return "Default"


def _mas_model_label() -> str:
    return "Llama-PcapLog"


async def _run_single_agent(llm: LLMProvider, target_ip: str, question: str) -> dict:
    def _gather_raw():
        pkt = run_tshark(f"ip.addr == {target_ip}", PCAP_PATH)
        log = grep_system_logs(target_ip, LOG_PATH)
        return (pkt or "") + "\n---\n" + (log or "")

    t0  = time.perf_counter()
    raw = await asyncio.to_thread(_gather_raw)

    prompt = f"""You are a security analyst. Analyze the following network data for IP {target_ip}.

Question: {question}

Raw packet data (tshark):
{raw[:4000]}

Provide your verdict (Malicious or Benign) and a brief summary of your analysis."""

    res     = await llm.call(prompt)
    latency = time.perf_counter() - t0
    txt     = (res.get("text") or "").lower()
    verdict = "Malicious" if "malicious" in txt or "attack" in txt else "Benign"
    tokens  = res.get("tokens", 0)
    return {"verdict": verdict, "latency": latency, "tokens": tokens}


def _run_centralized(target_ip: str) -> dict:
    t0      = time.perf_counter()
    pkt     = run_tshark(f"ip.addr == {target_ip}", PCAP_PATH)
    log     = grep_system_logs(target_ip, LOG_PATH)
    data_str = (pkt or "") + " " + (log or "")
    alerts  = apply_snort_rules(data_str)
    latency = time.perf_counter() - t0
    verdict = "Malicious" if alerts else "Benign"
    return {"verdict": verdict, "latency": latency, "tokens": 0, "alerts": alerts}


async def run_single_iteration(
    test_cases,
    iteration_id: int,
    llm: LLMProvider,
    model_label: str,
    mas_llm: Optional[LLMProvider] = None,
):
    shared_bus.reset()
    _mas    = mas_llm if mas_llm else llm
    master  = MasterOrchestrator("Master", _mas)
    p_agent = LocalSecurityAgent("Packet", TaskType.PACKET_ANALYSIS, PCAP_PATH, llm=_mas)
    l_agent = LocalSecurityAgent("Log",    TaskType.LOG_ANALYSIS,    LOG_PATH,   llm=_mas)

    iter_results = []
    print(f"  [Iter {iteration_id}] MAS_Model={_mas_model_label()}, SA_Model={model_label}, cases={len(test_cases)}")

    for idx, case in enumerate(test_cases):
        print(f"    - Case {idx+1}/{len(test_cases)} IP: {case['target_ip']} ({case['ground_truth_label']})")
        expected = case["expected_answer"]["verdict"]

        # MAS
        try:
            outcome    = await master.run_scenario(case["question"], case["target_ip"])
            total_tok  = outcome["tokens"] + sum(r.tokens_consumed for r in outcome["reports"])
            mas_sr     = 1 if outcome["verdict"] == expected else 0
            mas_latency = outcome["latency"]
            mas_tokens  = total_tok
        except Exception as e:
            print(f"      MAS run failed: {e}")
            mas_sr, mas_latency, mas_tokens = 0, 0.0, 0
            outcome = {"verdict": "N/A"}

        # SA
        try:
            sa_out    = await _run_single_agent(llm, case["target_ip"], case["question"])
            sa_sr     = 1 if sa_out["verdict"] == expected else 0
            sa_latency = sa_out["latency"]
            sa_tokens  = sa_out["tokens"]
        except Exception as e:
            print(f"      SA run failed: {e}")
            sa_sr, sa_latency, sa_tokens = 0, 0.0, 0
            sa_out = {"verdict": "N/A"}

        # Rule-based
        try:
            c_out    = await asyncio.to_thread(_run_centralized, case["target_ip"])
            c_sr     = 1 if c_out["verdict"] == expected else 0
            c_latency = c_out["latency"]
            c_tokens  = c_out["tokens"]
        except Exception as e:
            print(f"      Centralized run failed: {e}")
            c_sr, c_latency, c_tokens = 0, 0.0, 0
            c_out = {"verdict": "N/A"}

        iter_results.append({
            "Iteration":       iteration_id,
            "Case_ID":         idx + 1,
            "Target_IP":       case["target_ip"],
            "Category":        case.get("ground_truth_label", "Unknown"),
            "Expected_Verdict": expected,
            "MAS_Model":       _mas_model_label(),
            "SA_Model":        model_label,
            "MAS_Verdict":     outcome.get("verdict", "N/A") if 'outcome' in locals() else "N/A",
            "MAS_SR":          mas_sr,
            "MAS_Latency":     round(mas_latency, 4),
            "MAS_Tokens":      mas_tokens,
            "SA_Verdict":      sa_out.get("verdict", "N/A") if 'sa_out' in locals() else "N/A",
            "SA_SR":           sa_sr,
            "SA_Latency":      round(sa_latency, 4),
            "SA_Tokens":       sa_tokens,
            "C_Verdict":       c_out.get("verdict", "N/A") if 'c_out' in locals() else "N/A",
            "C_SR":            c_sr,
            "C_Latency":       round(c_latency, 4),
            "C_Tokens":        c_tokens,
        })
    return iter_results


# ── 통계 헬퍼 ────────────────────────────────────────────────────────────────
def _write_full_metrics_report(df: pd.DataFrame, single_model: bool = True):
    rows = []
    for arch, sr_col, lt_col, tok_col in [
        ("MAS",        "MAS_SR", "MAS_Latency", "MAS_Tokens"),
        ("SA",         "SA_SR",  "SA_Latency",  "SA_Tokens"),
        ("Rule-based", "C_SR",   "C_Latency",   "C_Tokens"),
    ]:
        rows += [
            {"Architecture": arch, "Metric": "Success Rate", "Value": round(df[sr_col].mean(),  4)},
            {"Architecture": arch, "Metric": "Latency (s)",  "Value": round(df[lt_col].mean(),  4)},
            {"Architecture": arch, "Metric": "Tokens/task",  "Value": round(df[tok_col].mean(), 2)},
        ]
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(RESULTS_DIR, "full_metrics_report.csv"), index=False)

    print("\n" + "=" * 70)
    print("ARCHITECTURE COMPARISON")
    print("=" * 70)
    print(f"{'Architecture':<15} {'Success Rate':<15} {'Latency (s)':<15} {'Tokens':<15}")
    print("-" * 70)
    for arch, sr_col, lt_col, tok_col in [
        ("MAS",        "MAS_SR", "MAS_Latency", "MAS_Tokens"),
        ("SA",         "SA_SR",  "SA_Latency",  "SA_Tokens"),
        ("Rule-based", "C_SR",   "C_Latency",   "C_Tokens"),
    ]:
        print(f"{arch:<15} {df[sr_col].mean():<15.4f} {df[lt_col].mean():<15.4f} {df[tok_col].mean():<15.0f}")
    print("=" * 70)


def _summary_by_arch(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for arch in ["MAS", "SA", "C"]:
        prefix = arch + "_"
        rows.append({
            "Arch":    arch,
            "SR":      round(df[prefix + "SR"].mean(),      2),
            "Latency": round(df[prefix + "Latency"].mean(), 2),
            "Tokens":  round(df[prefix + "Tokens"].mean(),  2),
        })
    return pd.DataFrame(rows)


def _print_summary(df: pd.DataFrame):
    print("\n" + "=" * 60)
    print("FINAL COMPARATIVE REPORT")
    print("=" * 60)
    print(_summary_by_arch(df).to_string(index=False))


# ── 실험 1: 3-way 반복 비교 (MAS / SA / Rule-based) ──────────────────────────
async def run_final_repeated_experiment(num_iterations: int = 3):
    """CMAF vs Single-Agent vs Rule-based 반복 비교 실험.

    출력:
      results/final_experiment_results.csv   — 케이스별 원시 데이터
      results/full_metrics_report.csv        — 아키텍처별 요약
      results/final_statistical_metrics.csv  — 반복 평균
    """
    if not os.path.exists(DATASET_PATH):
        return
    shared_bus.clear_pubsub_log()
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        test_cases = json.load(f)
    llm = LLMProvider()
    try:
        mas_llm = LLMProvider(backend=MAS_LLM_BACKEND, model=MAS_LLM_MODEL)
    except Exception:
        mas_llm = llm
    model_label = _model_label("auto", None)
    all_raw_data = []
    for i in range(1, num_iterations + 1):
        iteration_data = await run_single_iteration(test_cases, i, llm, model_label, mas_llm=mas_llm)
        all_raw_data.extend(iteration_data)
    final_df = pd.DataFrame(all_raw_data)
    final_df.to_csv(os.path.join(RESULTS_DIR, "final_experiment_results.csv"), index=False)
    _write_full_metrics_report(final_df, single_model=True)
    _print_summary(final_df)
    _summary_by_arch(final_df).to_csv(
        os.path.join(RESULTS_DIR, "final_statistical_metrics.csv"), index=False
    )


# ── 실험 2: 모델별 비교 (Category,Model,SR,Latency,Tokens 포맷) ───────────────
async def run_experiment_by_models(
    num_iterations: int = 1,
    llm_configs: Optional[list[tuple[str, Optional[str]]]] = None,
):
    if not os.path.exists(DATASET_PATH):
        print(f"Dataset not found: {DATASET_PATH}")
        return

    shared_bus.clear_pubsub_log()
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    configs = llm_configs or LLM_CONFIGS
    all_rows: list = []

    # MAS LLM 초기화
    try:
        mas_llm = LLMProvider(backend=MAS_LLM_BACKEND, model=MAS_LLM_MODEL)
        print(f"[MAS] {MAS_LLM_BACKEND}/{MAS_LLM_MODEL}")
    except Exception as e:
        print(f"[MAS] init failed: {e} — fallback 사용")
        mas_llm = None

    # ── 1. CMAF (multi-agent) 실행 ───────────────────────────────────
    for iteration in range(1, num_iterations + 1):
        print(f"\n[CMAF / multi-agent] iter={iteration}")
        shared_bus.reset()
        _mas   = mas_llm or LLMProvider()
        master = MasterOrchestrator("Master", _mas)
        LocalSecurityAgent("Packet", TaskType.PACKET_ANALYSIS, PCAP_PATH, llm=_mas)
        LocalSecurityAgent("Log",    TaskType.LOG_ANALYSIS,    LOG_PATH,   llm=_mas)
        for idx, case in enumerate(test_cases):
            expected = case["expected_answer"]["verdict"]
            print(f"  - Case {idx+1}/{len(test_cases)} IP: {case['target_ip']} ({case.get('ground_truth_label','?')})")
            try:
                outcome = await master.run_scenario(case["question"], case["target_ip"])
                sr      = 1 if outcome["verdict"] == expected else 0
                latency = round(outcome["latency"], 2)
                tokens  = outcome["tokens"] + sum(r.tokens_consumed for r in outcome["reports"])
            except Exception as e:
                print(f"    MAS failed: {e}")
                sr, latency, tokens = 0, 0.0, 0
            all_rows.append({
                "Category": case.get("ground_truth_label", "Unknown"),
                "Model":    "multi-agent",
                "SR":       sr,
                "Latency":  latency,
                "Tokens":   tokens,
            })

    # ── 2. 각 SA 모델 실행 ───────────────────────────────────────────
    for backend, model in []:
        label = _model_label(backend, model)
        try:
            llm = LLMProvider(backend=backend, model=model)
        except Exception as e:
            print(f"[Skip] {label}: {e}")
            continue
        for iteration in range(1, num_iterations + 1):
            print(f"\n[SA / {label}] iter={iteration}")
            for idx, case in enumerate(test_cases):
                expected = case["expected_answer"]["verdict"]
                print(f"  - Case {idx+1}/{len(test_cases)} IP: {case['target_ip']} ({case.get('ground_truth_label','?')})")
                try:
                    sa_out  = await _run_single_agent(llm, case["target_ip"], case["question"])
                    sr      = 1 if sa_out["verdict"] == expected else 0
                    latency = round(sa_out["latency"], 2)
                    tokens  = sa_out["tokens"]
                except Exception as e:
                    print(f"    SA failed: {e}")
                    sr, latency, tokens = 0, 0.0, 0
                all_rows.append({
                    "Category": case.get("ground_truth_label", "Unknown"),
                    "Model":    label,
                    "SR":       sr,
                    "Latency":  latency,
                    "Tokens":   tokens,
                })

    if not all_rows:
        print("결과 없음.")
        return

    df = pd.DataFrame(all_rows)
    out_path = os.path.join(RESULTS_DIR, "experiment_by_model.csv")
    df.to_csv(out_path, index=False)
    print(f"\nSaved: {out_path}")

    # 모델별 요약
    print("\n" + "=" * 60)
    print("MODEL COMPARISON SUMMARY")
    print("=" * 60)
    print(f"{'Model':<28} {'SR':>8} {'Latency(s)':>12} {'Tokens':>10}")
    print("-" * 60)
    summary_rows = []
    for model_name in df["Model"].unique():
        sub = df[df["Model"] == model_name]
        sr_mean  = sub["SR"].mean()
        lat_mean = sub["Latency"].mean()
        tok_mean = sub["Tokens"].mean()
        print(f"  {model_name:<26} {sr_mean:>8.4f} {lat_mean:>10.2f}s {tok_mean:>10.1f}")
        summary_rows.append({
            "Model":   model_name,
            "Arch":    "MAS" if model_name == "multi-agent" else "SA",
            "SR":      round(sr_mean,  4),
            "Latency": round(lat_mean, 4),
            "Tokens":  round(tok_mean, 2),
        })
    print("=" * 60)

    pd.DataFrame(summary_rows).to_csv(
        os.path.join(RESULTS_DIR, "experiment_by_model_summary.csv"), index=False
    )
    print(f"Saved: {RESULTS_DIR}/experiment_by_model_summary.csv")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "by-model":
        asyncio.run(run_experiment_by_models(num_iterations=1))
    else:
        asyncio.run(run_final_repeated_experiment(num_iterations=3))
