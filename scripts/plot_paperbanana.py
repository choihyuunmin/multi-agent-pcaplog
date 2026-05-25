import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_DIR = os.path.join(ROOT, "results", "figures")
os.makedirs(OUT_DIR, exist_ok=True)

METHOD_ORDER = [
    "Multi-agent\n(Proposed)",
    "Rule-based",
    "GPT-5",
    "Gemini 3",
    "DeepSeek-R1",
    "Llama 3",
    "Qwen 3",
]

# PaperBanana inspired aesthetics
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
    "grid.alpha": 0.7,
})

def load_flat_comparison():
    path_summary = os.path.join(ROOT, "results", "experiment_by_model_summary.csv")
    df = pd.read_csv(path_summary)
    
    result = {m: {"SR": 0.0, "Latency": 0.0, "Tokens": 0.0} for m in METHOD_ORDER}
    
    for _, row in df.iterrows():
        model_key = str(row["Model"]).lower()
        arch = str(row["Arch"]).upper() if pd.notna(row["Arch"]) else ""
        
        target_key = None
        if model_key == "mas" or arch == "MAS":
            target_key = "Multi-agent\n(Proposed)"
        elif model_key == "rule" or arch == "RULE":
            target_key = "Rule-based"
        elif "gpt" in model_key or "gpt-5" in model_key:
            target_key = "GPT-5"
        elif "gemini" in model_key:
            target_key = "Gemini 3"
        elif "deepseek" in model_key:
            target_key = "DeepSeek-R1"
        elif "llama" in model_key:
            target_key = "Llama 3"
        elif "qwen" in model_key:
            target_key = "Qwen 3"
            
        if target_key:
            result[target_key]["SR"] = row["SR"]
            result[target_key]["Latency"] = row["Latency"]
            result[target_key]["Tokens"] = row["Tokens"]
            
    return result

def draw_paperbanana_style():
    data = load_flat_comparison()
    methods = METHOD_ORDER
    n = len(methods)
    x = np.arange(n)
    width = 0.65

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    plt.subplots_adjust(wspace=0.25)
    
    sr_vals = [data[m]["SR"] for m in methods]
    lat_vals = [data[m]["Latency"] for m in methods]
    tok_vals = [data[m]["Tokens"] for m in methods]

    # Color palette: Highlight proposed method
    colors = ["#2c5282"] + ["#a0aec0"] * (n - 1)
    edge_colors = ["#1a365d"] + ["#718096"] * (n - 1)

    # 1. Success Rate
    ax = axes[0]
    bars = ax.bar(x, sr_vals, width=width, color=colors, edgecolor=edge_colors, linewidth=1.2)
    for j, v in enumerate(sr_vals):
        if v > 0:
            ax.text(x[j], v + 0.02, f"{v:.2f}", ha="center", va="bottom", fontsize=10, fontweight="bold" if j==0 else "normal", color="#2d3748")
    ax.set_xticks(x)
    ax.set_xticklabels(methods, rotation=35, ha="right")
    ax.set_ylabel("Success Rate")
    ax.set_title("(a) Accuracy (Success Rate)")
    ax.set_ylim(0, 1.1)

    # 2. Latency
    ax = axes[1]
    bars = ax.bar(x, lat_vals, width=width, color=colors, edgecolor=edge_colors, linewidth=1.2)
    for j, v in enumerate(lat_vals):
        if v > 0:
            ax.text(x[j], v + 0.5, f"{v:.2f}s", ha="center", va="bottom", fontsize=10, fontweight="bold" if j==0 else "normal", color="#2d3748")
    ax.set_xticks(x)
    ax.set_xticklabels(methods, rotation=35, ha="right")
    ax.set_ylabel("Latency (Seconds)")
    ax.set_title("(b) Inference Speed")
    ax.set_ylim(0, max(lat_vals) * 1.15 if lat_vals else 1)

    # 3. Tokens
    ax = axes[2]
    bars = ax.bar(x, tok_vals, width=width, color=colors, edgecolor=edge_colors, linewidth=1.2)
    for j, v in enumerate(tok_vals):
        if v > 0:
            ax.text(x[j], v + 50, f"{v:.0f}", ha="center", va="bottom", fontsize=10, fontweight="bold" if j==0 else "normal", color="#2d3748")
    ax.set_xticks(x)
    ax.set_xticklabels(methods, rotation=35, ha="right")
    ax.set_ylabel("Total Tokens Consumed")
    ax.set_title("(c) Token Efficiency")
    ax.set_ylim(0, max(tok_vals) * 1.15 if tok_vals else 1)

    plt.tight_layout()
    out_pdf = os.path.join(OUT_DIR, "fig_by_model_paperbanana.pdf")
    out_png = os.path.join(OUT_DIR, "fig_by_model_paperbanana.png")
    
    plt.savefig(out_pdf, bbox_inches="tight")
    plt.savefig(out_png, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"PaperBanana style plots generated: {out_png}")

if __name__ == "__main__":
    draw_paperbanana_style()
