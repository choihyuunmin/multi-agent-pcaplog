import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

out_dir = "/Users/choi/학교/연구/ICETC journal/2026_ICETC_transactions"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_DIR = os.path.join(ROOT, "results", "figures")
os.makedirs(OUT_DIR, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
})

def draw_box(ax, text, xy, width, height, facecolor='#E8F0F9', edgecolor='#4C72B0', text_color='black', fontsize=10, font_weight='bold'):
    shadow = patches.FancyBboxPatch(
        (xy[0]+0.08, xy[1]-0.08), width, height,
        boxstyle="round,pad=0.1", facecolor='black', alpha=0.15, edgecolor='none'
    )
    ax.add_patch(shadow)
    
    box = patches.FancyBboxPatch(
        xy, width, height,
        boxstyle="round,pad=0.1",
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=1.5
    )
    ax.add_patch(box)
    
    ax.text(xy[0] + width/2, xy[1] + height/2, text, 
            ha='center', va='center', fontsize=fontsize, fontweight=font_weight, 
            color=text_color, wrap=True, zorder=3)
    return box

def draw_arrow(ax, start, end, style="->", color="#333333", rad=0.0):
    ax.annotate('', xy=end, xytext=start,
                arrowprops=dict(arrowstyle=style, color=color, lw=2, connectionstyle=f"arc3,rad={rad}", 
                                shrinkA=5, shrinkB=5))

# --- 1. Coordinator Workflow (Figure 3) - Single Column Vertical ---
def plot_coordinator_workflow():
    fig, ax = plt.subplots(figsize=(6, 9))  # Vertical orientation (1-column fit)
    ax.set_xlim(0, 6)
    ax.set_ylim(0, 9.5)
    ax.axis('off')
    
    # Boundary
    coord_box = patches.Rectangle((0.2, 1.0), 5.6, 7.3, fill=True, facecolor='#f8f9fa', edgecolor='#ced4da', linewidth=2, linestyle='--', zorder=0)
    ax.add_patch(coord_box)
    ax.text(3.0, 8.1, "Multi-Agent Coordinator Node", ha='center', va='center', fontsize=12, fontweight='bold', color='#495057')

    # Top to bottom flow
    draw_box(ax, "User Security Query\n(Natural Language)", (1.5, 8.6), 3.0, 0.6, facecolor='#eceff1', edgecolor='#607d8b', fontsize=11)
    
    draw_arrow(ax, (3.0, 8.6), (3.0, 7.7))
    
    draw_box(ax, "1. Intent Extraction\n(LLM Router, Entity Extractor)", (1.2, 6.7), 3.6, 0.9, facecolor='#e3f2fd', edgecolor='#1e88e5')
    
    draw_arrow(ax, (3.0, 6.7), (3.0, 5.7))
    
    draw_box(ax, "2. Domain Evidence\nCollection Engine", (1.2, 4.8), 3.6, 0.8, facecolor='#fff3e0', edgecolor='#f4511e')
    
    # Agents (fan out)
    draw_arrow(ax, (2.0, 4.8), (1.2, 4.2), color="#f4511e")
    draw_arrow(ax, (3.0, 4.8), (3.0, 4.2), color="#f4511e")
    draw_arrow(ax, (4.0, 4.8), (4.8, 4.2), color="#f4511e")
    
    draw_box(ax, "PCAP\nAgent", (0.5, 3.4), 1.2, 0.7, facecolor='#fce4ec', edgecolor='#d81b60', fontsize=9)
    draw_box(ax, "SysLog\nAgent", (2.4, 3.4), 1.2, 0.7, facecolor='#fce4ec', edgecolor='#d81b60', fontsize=9)
    draw_box(ax, "Threat\nIntel", (4.3, 3.4), 1.2, 0.7, facecolor='#fce4ec', edgecolor='#d81b60', fontsize=9)
    
    # Wait Queue
    draw_box(ax, "3. Async Wait Queue\n& State Manager", (1.2, 1.8), 3.6, 0.8, facecolor='#f3e5f5', edgecolor='#8e24aa', fontsize=11)
    
    # Agents to Wait Queue
    draw_arrow(ax, (1.1, 3.4), (2.0, 2.7), color="#8e24aa")
    draw_arrow(ax, (3.0, 3.4), (3.0, 2.7), color="#8e24aa")
    draw_arrow(ax, (4.9, 3.4), (4.0, 2.7), color="#8e24aa")
    
    # Queue to Aggregation
    draw_arrow(ax, (3.0, 1.8), (3.0, 1.2), color="#43a047")
    
    draw_box(ax, "4. Confidence-Weighted\nAggregation", (1.2, 0.3), 3.6, 0.8, facecolor='#e8f5e9', edgecolor='#43a047')
    
    # Output
    draw_arrow(ax, (3.0, 0.3), (3.0, -0.4))
    draw_box(ax, "Final Investigation Report", (1.5, -0.9), 3.0, 0.5, facecolor='#eceff1', edgecolor='#607d8b', fontsize=11)
    
    # Adjust axes to prevent cutoff
    ax.set_ylim(-1.2, 9.5)
    
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'b-figure_coordinator_workflow.png'), dpi=300, bbox_inches='tight', pad_inches=0.2)
    plt.close()


# --- 2. Structured Data Schema (Figure 4) - Single Column Vertical ---
def plot_structured_schema():
    fig, ax = plt.subplots(figsize=(6, 8.5)) # Tall orientation
    ax.set_xlim(0, 6)
    ax.set_ylim(0, 8.5)
    ax.axis('off')

    # Background
    bg = patches.Rectangle((0.2, 0.2), 5.6, 7.8, fill=True, facecolor='#f4f6f9', edgecolor='#b0bec5', linewidth=1.5, zorder=0)
    ax.add_patch(bg)
    ax.text(3.0, 7.7, "Pub/Sub Distributed Message Schema", ha='center', va='center', fontsize=13, fontweight='bold', color='#263238')

    # Top: Base Envelope
    draw_box(ax, "Message Envelope\n(EventBus Wrapper)", (0.6, 6.4), 4.8, 1.0, facecolor='#e0f2f1', edgecolor='#00897b', fontsize=11)
    ax.text(1.0, 6.2, "Fields: msg_id, timestamp, source_agent, target_agent", fontsize=9, va='top', color='#00695c')

    # Arrow down
    draw_arrow(ax, (3.0, 6.1), (3.0, 5.6), style="-|>", color="#00897b")
    ax.text(3.2, 5.8, "encapsulates", ha='left', fontsize=10, fontstyle='italic', color='#00897b')

    # Bottom: Payload Interface
    draw_box(ax, "Payload: AgentIntelligence", (0.6, 1.8), 4.8, 3.7, facecolor='#ffffff', edgecolor='#3949ab', fontsize=12)
    
    # Attributes
    draw_box(ax, "verdict: boolean", (1.0, 4.6), 4.0, 0.5, facecolor='#e8eaf6', edgecolor='#5c6bc0', fontsize=10)
    ax.text(1.2, 4.4, "Binary indicator of threat detection.", fontsize=8, color='#555', va='top')
    
    draw_box(ax, "confidence: float", (1.0, 3.6), 4.0, 0.5, facecolor='#e8eaf6', edgecolor='#5c6bc0', fontsize=10)
    ax.text(1.2, 3.4, "LLM-calibrated certainty [0.0 - 1.0].", fontsize=8, color='#555', va='top')
    
    draw_box(ax, "evidence_summary: text", (1.0, 2.6), 4.0, 0.5, facecolor='#e8eaf6', edgecolor='#5c6bc0', fontsize=10)
    ax.text(1.2, 2.4, "Natural language rationale of findings.", fontsize=8, color='#555', va='top')

    # JSON Snippet at bottom
    code_text = "{\n  \"msg_id\": \"b8...\",\n  \"payload\": {\n    \"verdict\": true,\n    \"confidence\": 0.95\n  }\n}"
    ax.text(3.0, 0.6, code_text, family='monospace', fontsize=9, 
            bbox=dict(facecolor='#263238', edgecolor='none', boxstyle='round,pad=0.5'), color='#80cbc4', ha='center', va='center')

    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'b-figure_structured_data.png'), dpi=300, bbox_inches='tight', pad_inches=0.2)
    plt.close()


if __name__ == "__main__":
    plot_coordinator_workflow()
    plot_structured_schema()
    print("Single-column PaperBanana style Diagrams successfully generated.")
