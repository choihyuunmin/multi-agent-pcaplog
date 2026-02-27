import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_DIR = os.path.join(ROOT, "results", "figures")
os.makedirs(OUT_DIR, exist_ok=True)

# 차트 X축 순서: 7개 방법
METHOD_ORDER = [
    "Multi-agent",
    "Rule-based",
    "GPT5",
    "Gemini3",
    "DeepSeek-R1",
    "Llama",
    "Qwen3",
]
def load_flat_comparison():
    """experiment_by_model_summary.csv를 읽어 7개 방법별 SR/Latency/Tokens로 매핑."""
    path_summary = os.path.join(ROOT, "results", "experiment_by_model_summary.csv")
    if not os.path.exists(path_summary):
        raise FileNotFoundError(
            "experiment_by_model_summary.csv가 없습니다. 먼저 실행하세요: ./run.sh experiment-by-model"
        )

    df = pd.read_csv(path_summary)
    result = {m: {"SR": 0.0, "Latency": 0.0, "Tokens": 0.0} for m in METHOD_ORDER}

    # summary 형식: Model, Arch, SR, Latency, Tokens
    # Model=MAS/Rule 또는 모델명(gpt-5, gemini 등), Arch=MAS/Rule/SA
    for _, row in df.iterrows():
        model_key = str(row["Model"]).lower()
        arch = str(row["Arch"]).upper() if pd.notna(row["Arch"]) else ""

        if model_key == "mas" or arch == "MAS":
            result["Multi-agent"]["SR"] = row["SR"]
            result["Multi-agent"]["Latency"] = row["Latency"]
            result["Multi-agent"]["Tokens"] = row["Tokens"]
        elif model_key == "rule" or arch == "RULE":
            result["Rule-based"]["SR"] = row["SR"]
            result["Rule-based"]["Latency"] = row["Latency"]
            result["Rule-based"]["Tokens"] = row["Tokens"]
        elif "gpt" in model_key or "gpt-5" in model_key:
            result["GPT5"]["SR"] = row["SR"]
            result["GPT5"]["Latency"] = row["Latency"]
            result["GPT5"]["Tokens"] = row["Tokens"]
        elif "gemini" in model_key:
            result["Gemini3"]["SR"] = row["SR"]
            result["Gemini3"]["Latency"] = row["Latency"]
            result["Gemini3"]["Tokens"] = row["Tokens"]
        elif "deepseek" in model_key:
            result["DeepSeek-R1"]["SR"] = row["SR"]
            result["DeepSeek-R1"]["Latency"] = row["Latency"]
            result["DeepSeek-R1"]["Tokens"] = row["Tokens"]
        elif "llama" in model_key:
            result["Llama"]["SR"] = row["SR"]
            result["Llama"]["Latency"] = row["Latency"]
            result["Llama"]["Tokens"] = row["Tokens"]
        elif "qwen" in model_key:
            result["Qwen3"]["SR"] = row["SR"]
            result["Qwen3"]["Latency"] = row["Latency"]
            result["Qwen3"]["Tokens"] = row["Tokens"]

    return result


def plot_by_model():
    data = load_flat_comparison()
    methods = METHOD_ORDER
    n = len(methods)
    x = np.arange(n)
    width = 0.6

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    plt.subplots_adjust(wspace=0.3)
    fig.set_facecolor("#fafafa")
    plt.rcParams.update({
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
    })

    for ax in axes:
        ax.set_facecolor("white")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    sr_vals = [data[m]["SR"] for m in methods]
    lat_vals = [data[m]["Latency"] for m in methods]
    tok_vals = [data[m]["Tokens"] for m in methods]

    colors = plt.cm.Set3(np.linspace(0, 1, n))

    ax = axes[0]
    bars = ax.bar(x, sr_vals, width=width * 0.9, color=colors, edgecolor="white", linewidth=0.8)
    for j, v in enumerate(sr_vals):
        if v > 0:
            ax.text(x[j], v + 0.02, f"{v:.2f}", ha="center", va="bottom", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels(methods, rotation=25, ha="right")
    ax.set_ylabel("Success Rate")
    ax.set_title("(a) Success Rate")
    ax.set_ylim(0, 1.15)
    ax.yaxis.grid(True, alpha=0.35)

    ax = axes[1]
    ax.bar(x, lat_vals, width=width * 0.9, color=colors, edgecolor="white", linewidth=0.8)
    for j, v in enumerate(lat_vals):
        if v > 0:
            ax.text(x[j], v + 0.01, f"{v:.2f}s", ha="center", va="bottom", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels(methods, rotation=25, ha="right")
    ax.set_ylabel("Latency (s)")
    ax.set_title("(b) Latency")
    ax.set_ylim(0, max(lat_vals) * 1.2 if lat_vals else 1)
    ax.yaxis.grid(True, alpha=0.35)

    ax = axes[2]
    ax.bar(x, tok_vals, width=width * 0.9, color=colors, edgecolor="white", linewidth=0.8)
    for j, v in enumerate(tok_vals):
        if v > 0:
            ax.text(x[j], v + 50, f"{v:.2f}", ha="center", va="bottom", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels(methods, rotation=25, ha="right")
    ax.set_ylabel("Tokens")
    ax.set_title("(c) Tokens")
    ax.set_ylim(0, max(tok_vals) * 1.15 if tok_vals else 1)
    ax.yaxis.grid(True, alpha=0.35)

    plt.savefig(os.path.join(OUT_DIR, "fig_by_model.pdf"), bbox_inches="tight", pad_inches=0.08, facecolor=fig.get_facecolor())
    plt.savefig(os.path.join(OUT_DIR, "fig_by_model.png"), dpi=300, bbox_inches="tight", pad_inches=0.08, facecolor=fig.get_facecolor())
    plt.close()

    # 차트와 동일한 데이터 CSV 저장
    fig_data = pd.DataFrame([
        {"Method": m, "SR": round(data[m]["SR"], 2), "Latency": round(data[m]["Latency"], 2), "Tokens": round(data[m]["Tokens"], 2)}
        for m in methods
    ])
    csv_path = os.path.join(ROOT, "results", "fig_by_model_data.csv")
    fig_data.to_csv(csv_path, index=False)
    print(f"[OK] Saved {OUT_DIR}/fig_by_model.pdf, .png and {csv_path}")


if __name__ == "__main__":
    plot_by_model()
