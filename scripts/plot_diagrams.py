import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os

out_dir = "/Users/choi/학교/연구/ICETC journal/2026_ICETC_transactions"

def draw_box(ax, text, xy, width, height, facecolor='#E8F0F9', edgecolor='#4C72B0'):
    box = patches.FancyBboxPatch(
        xy, width, height,
        boxstyle="round,pad=0.1",
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=2
    )
    ax.add_patch(box)
    ax.text(xy[0] + width/2, xy[1] + height/2, text, 
            ha='center', va='center', fontsize=12, fontweight='bold', wrap=True)

def draw_arrow(ax, start, end):
    ax.annotate('', xy=end, xytext=start,
                arrowprops=dict(facecolor='black', edgecolor='black', width=2, headwidth=10, shrink=0.05))

# --- 1. Coordinator Workflow ---
fig, ax = plt.subplots(figsize=(10, 3))
ax.set_xlim(0, 10)
ax.set_ylim(0, 3)
ax.axis('off')

# Boxes
draw_box(ax, "1. Intent\nExtraction", (0.5, 1), 1.8, 1)
draw_box(ax, "2. Domain Evidence\nCollection", (3.0, 1), 2.0, 1, facecolor='#FDE3E3', edgecolor='#C44E52')
draw_box(ax, "3. Wait for\nReports", (5.7, 1), 1.6, 1)
draw_box(ax, "4. Confidence-Weighted\nAggregation", (8.0, 1), 2.2, 1, facecolor='#E4F0E6', edgecolor='#55A868')

# Arrows
draw_arrow(ax, (2.3, 1.5), (3.0, 1.5))
draw_arrow(ax, (5.0, 1.5), (5.7, 1.5))
draw_arrow(ax, (7.3, 1.5), (8.0, 1.5))

plt.title("Coordinator Operational Workflow", fontsize=16, fontweight='bold', pad=10)
plt.tight_layout()
plt.savefig(os.path.join(out_dir, 'b-figure_coordinator_workflow.png'), dpi=300)
plt.close()

# --- 2. Structured Data Schema ---
fig, ax = plt.subplots(figsize=(8, 6))
ax.set_xlim(0, 8)
ax.set_ylim(0, 6)
ax.axis('off')

# Main Message Box
main_box = patches.Rectangle((0.5, 0.5), 7, 5, fill=False, edgecolor='gray', linewidth=2, linestyle='--')
ax.add_patch(main_box)
ax.text(4, 5.7, "Pub/Sub Message Schema (JSON)", ha='center', va='center', fontsize=14, fontweight='bold')

# Header
draw_box(ax, "Message Header\n- Task ID\n- Correlation ID\n- Timestamp", (1, 3.5), 2.5, 1.2, facecolor='#E8E8E8', edgecolor='gray')

# Payload (AgentIntelligence)
draw_box(ax, "Payload: AgentIntelligence", (4, 4.0), 3, 0.7, facecolor='#E8F0F9', edgecolor='#4C72B0')

# Payload fields
draw_box(ax, "verdict: bool", (4.2, 3.0), 2.6, 0.5, facecolor='white', edgecolor='#4C72B0')
draw_box(ax, "confidence: float (0~1)", (4.2, 2.3), 2.6, 0.5, facecolor='white', edgecolor='#4C72B0')
draw_box(ax, "evidence_summary: str", (4.2, 1.6), 2.6, 0.5, facecolor='white', edgecolor='#4C72B0')
draw_box(ax, "tool_calls: List[ToolCall]", (4.2, 0.9), 2.6, 0.5, facecolor='white', edgecolor='#4C72B0')

# Arrow from Header/Payload context
draw_arrow(ax, (3.5, 4.1), (4.0, 4.3))

plt.tight_layout()
plt.savefig(os.path.join(out_dir, 'b-figure_structured_data.png'), dpi=300)
plt.close()

print("Diagrams successfully generated and saved to the manuscript directory.")
