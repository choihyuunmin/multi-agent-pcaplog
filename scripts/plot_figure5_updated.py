import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_DIR = os.path.join(ROOT, "results", "figures")
os.makedirs(OUT_DIR, exist_ok=True)

METHOD_ORDER = [
    "Multi-agent",
    "Rule-based",
    "GPT-5",
    "Gemini 3",
    "DeepSeek-R1",
    "Llama 3",
    "Qwen 3",
]

RTT_MAP = {
    "gpt-5": 0.20,
    "gemini": 0.15,
}

MODEL_COLORS = {
    "Multi-agent": "#8dd3c7",
    "Rule-based": "#ffffb3",
    "GPT-5": "#bebada",
    "Gemini 3": "#fb8072",
    "DeepSeek-R1": "#80b1d3",
    "Llama 3": "#fdb462",
    "Qwen 3": "#b3de69",
}

MODEL_EDGE_COLORS = {
    "Multi-agent": "#5e9d94",
    "Rule-based": "#c7c777",
    "GPT-5": "#8f8ab0",
    "Gemini 3": "#c55e54",
    "DeepSeek-R1": "#5d85a2",
    "Llama 3": "#c38642",
    "Qwen 3": "#83aa45",
}

RAW_RESULT_OVERRIDES = {"Multi-agent", "GPT-5", "Gemini 3"}

def _empty_result():
    return {m: {"SR": 0.0, "Latency": 0.0, "Tokens": 0.0} for m in METHOD_ORDER}


def _target_key(model_name: str, arch: str = ""):
    model_key = str(model_name).lower()
    arch_key = str(arch).upper() if pd.notna(arch) else ""

    if model_key in {"mas", "multi-agent"} or arch_key == "MAS":
        return "Multi-agent"
    if model_key in {"rule", "rule-based"} or arch_key == "RULE":
        return "Rule-based"
    if "gpt" in model_key:
        return "GPT-5"
    if "gemini" in model_key:
        return "Gemini 3"
    if "deepseek" in model_key:
        return "DeepSeek-R1"
    if "llama" in model_key:
        return "Llama 3"
    if "qwen" in model_key:
        return "Qwen 3"
    return None


def _pure_latency(model_name: str, latency: float) -> float:
    model_key = str(model_name).lower()
    for key, rtt in RTT_MAP.items():
        if key in model_key:
            return max(0.0, latency - rtt)
    return latency


def load_and_adjust_data():
    """Load Fig. 5 values.

    Prefer experiment_by_model_summary.csv because it may contain measured
    baseline rows that are absent from a partial rerun of experiment_by_model.csv.
    Fall back to the raw per-case CSV for any missing model.
    """
    result = _empty_result()

    path_summary = os.path.join(ROOT, "results", "experiment_by_model_summary.csv")
    if os.path.exists(path_summary):
        summary = pd.read_csv(path_summary)
        for _, row in summary.iterrows():
            target_key = _target_key(row["Model"], row.get("Arch", ""))
            if not target_key:
                continue
            result[target_key]["SR"] = float(row["SR"])
            result[target_key]["Latency"] = _pure_latency(row["Model"], float(row["Latency"]))
            result[target_key]["Tokens"] = float(row["Tokens"])

    path_raw = os.path.join(ROOT, "results", "experiment_by_model.csv")
    if os.path.exists(path_raw):
        raw = pd.read_csv(path_raw)
        means = raw.groupby("Model").mean(numeric_only=True).reset_index()
        for _, row in means.iterrows():
            target_key = _target_key(row["Model"])
            if not target_key:
                continue
            # Partial reruns should update rows that are present in the latest
            # raw experiment results, while preserving baselines absent there.
            has_value = any(result[target_key][k] for k in ("SR", "Latency", "Tokens"))
            if target_key in RAW_RESULT_OVERRIDES or not has_value:
                result[target_key]["SR"] = float(row["SR"])
                result[target_key]["Latency"] = _pure_latency(row["Model"], float(row["Latency"]))
                result[target_key]["Tokens"] = float(row["Tokens"])

    # Save the updated summary for record
    summary_df = pd.DataFrame([
        {"Model": m, "SR": result[m]["SR"], "Latency_Pure": result[m]["Latency"], "Tokens": result[m]["Tokens"]}
        for m in METHOD_ORDER
    ])
    summary_df.to_csv(os.path.join(ROOT, "results", "updated_experiment_summary.csv"), index=False)
    summary_df.rename(columns={"Model": "Method", "Latency_Pure": "Latency"}).to_csv(
        os.path.join(ROOT, "results", "fig_by_model_data.csv"), index=False
    )
    
    return result

def draw_figure5():
    data = load_and_adjust_data()
    methods = METHOD_ORDER
    n = len(methods)
    x = np.arange(n)
    width = 0.65

    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
        "axes.titlesize": 14,
        "axes.labelsize": 12,
        "xtick.labelsize": 11,
        "ytick.labelsize": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": "#e0e0e0",
        "grid.linestyle": "--",
    })

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    plt.subplots_adjust(wspace=0.25)
    
    sr_vals = [data[m]["SR"] for m in methods]
    lat_vals = [data[m]["Latency"] for m in methods]
    tok_vals = [data[m]["Tokens"] for m in methods]

    colors = [MODEL_COLORS[m] for m in methods]
    edge_colors = [MODEL_EDGE_COLORS[m] for m in methods]

    # 1. Success Rate
    ax = axes[0]
    ax.bar(x, sr_vals, width=width, color=colors, edgecolor=edge_colors, linewidth=1.2)
    for j, v in enumerate(sr_vals):
        if v > 0:
            ax.text(x[j], v + 0.02, f"{v:.2f}", ha="center", va="bottom", fontsize=10, fontweight="bold" if j==0 else "normal")
    ax.set_xticks(x)
    ax.set_xticklabels(methods, rotation=35, ha="right")
    ax.set_ylabel("Success Rate")
    ax.set_title("(a) Accuracy (Success Rate)")
    ax.set_ylim(0, 1.1)

    # 2. Latency
    ax = axes[1]
    ax.bar(x, lat_vals, width=width, color=colors, edgecolor=edge_colors, linewidth=1.2)
    for j, v in enumerate(lat_vals):
        if v > 0:
            ax.text(x[j], v + 0.5, f"{v:.2f}s", ha="center", va="bottom", fontsize=10, fontweight="bold" if j==0 else "normal")
    ax.set_xticks(x)
    ax.set_xticklabels(methods, rotation=35, ha="right")
    ax.set_ylabel("Pure Processing Latency (Seconds)")
    ax.set_title("(b) Inference Speed (Excluding RTT)")
    ax.set_ylim(0, max(lat_vals) * 1.15 if lat_vals else 1)

    # 3. Tokens
    ax = axes[2]
    ax.bar(x, tok_vals, width=width, color=colors, edgecolor=edge_colors, linewidth=1.2)
    for j, v in enumerate(tok_vals):
        if v > 0:
            ax.text(x[j], v + 50, f"{v:.0f}", ha="center", va="bottom", fontsize=10, fontweight="bold" if j==0 else "normal")
    ax.set_xticks(x)
    ax.set_xticklabels(methods, rotation=35, ha="right")
    ax.set_ylabel("Total Tokens Consumed")
    ax.set_title("(c) Token Efficiency")
    ax.set_ylim(0, max(tok_vals) * 1.15 if tok_vals else 1)

    plt.tight_layout()
    out_png = os.path.join(OUT_DIR, "b-figure03_updated.png")
    out_pdf = os.path.join(OUT_DIR, "b-figure03_updated.pdf")
    
    plt.savefig(out_png, dpi=300, bbox_inches="tight")
    plt.savefig(out_pdf, bbox_inches="tight")
    plt.close()
    print(f"Figure 5 updated and saved to: {out_png}")
    print(f"Figure 5 PDF saved to: {out_pdf}")

if __name__ == "__main__":
    draw_figure5()
