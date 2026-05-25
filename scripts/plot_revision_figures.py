import matplotlib.pyplot as plt
import numpy as np
import os

# Set output directory
out_dir = "/Users/choi/학교/연구/ICETC journal/2026_ICETC_transactions"

# 1. Latency RTT Stacked Bar Chart (b-figure_latency_rtt.png)
labels = ['Multi-Agent\nFramework', 'GPT-5\n(Single LLM)', 'Rule-based\nSystem']
pure_latency = [2.97, 30.14, 0.0]
network_rtt = [0.0, 0.20, 0.0]

fig, ax = plt.subplots(figsize=(8, 6))

width = 0.5
ax.bar(labels, pure_latency, width, label='Algorithmic Inference Time', color='#4C72B0', edgecolor='black')
ax.bar(labels, network_rtt, width, bottom=pure_latency, label='Network RTT (API Delay)', color='#DD8452', edgecolor='black')

ax.set_ylabel('Inference Latency (seconds)', fontsize=12)
ax.set_title('Latency Comparison: Network RTT vs Algorithmic Inference', fontsize=14, fontweight='bold')
ax.legend(fontsize=11)

# Annotations
for i in range(len(labels)):
    total = pure_latency[i] + network_rtt[i]
    ax.text(i, total + 0.3, f'{total:.2f}s', ha='center', fontweight='bold', fontsize=11)
    if network_rtt[i] > 0:
        ax.text(i, pure_latency[i] + network_rtt[i]/2, f'RTT: {network_rtt[i]}s', ha='center', va='center', color='white', fontweight='bold')

plt.tight_layout()
plt.savefig(os.path.join(out_dir, 'b-figure_latency_rtt.png'), dpi=300)
plt.close()

# 2. Hallucination Pie Chart (b-figure_hallucination_analysis.png)
labels_pie = ['Correctly Grounded\n(No Hallucination: 69%)', 'Benign Hallucination\n(Harmless Explanations: 31%)', 'Harmful Hallucination\n(Factual Errors: <0.5%)']
sizes = [68.6, 31.0, 0.4]
colors = ['#55A868', '#F1A340', '#C44E52']
explode = (0.05, 0.05, 0.1)

fig2, ax2 = plt.subplots(figsize=(8, 6))
ax2.pie(sizes, explode=explode, labels=labels_pie, colors=colors, autopct='%1.1f%%',
        shadow=True, startangle=140, textprops={'fontsize': 11, 'fontweight': 'bold'})
ax2.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
plt.title('Analysis of Model Hallucinations in Multi-Agent Framework', fontsize=14, fontweight='bold', pad=20)

plt.tight_layout()
plt.savefig(os.path.join(out_dir, 'b-figure_hallucination_analysis.png'), dpi=300)
plt.close()

print("Charts successfully generated and saved to the manuscript directory.")
