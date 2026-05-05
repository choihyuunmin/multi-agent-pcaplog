# multi-agent-pcaplog: Multi-Agent Security Analysis System

A multi-agent system for security threat detection. It uses the Llama-PcapLog model to distribute packet and log analysis across specialized agents.

## Paper

**A Collaborative Multi-Agent Framework for Network Packets and System Logs Analysis**

This paper proposes a collaborative multi-agent framework that analyzes network traffic and system logs together to detect complex multi-stage cyberattacks. Conventional security systems based on large language models (LLMs) have limitations such as outdated knowledge after fine-tuning and the inefficiency of retrieval-augmented generation (RAG) when handling structured or numeric network data.

To address these issues, the framework adopts a hierarchical and distributed architecture suitable for large-scale environments. A central coordinator component issues structured task directives, while multiple Network Analysis Agents operate close to the data sources. Instead of converting raw packets or logs into large text prompts, the system lets specialized agents extract domain-specific evidence. Each network analysis agent applies analytical tools directly to packet and log data and returns structured summaries. This design enables precise analysis while limiting token usage and reducing information loss.

Network Analysis Agents return summarized evidence and key indicators, which are integrated to reconstruct attack scenarios by verifying information across different data sources. By separating the coordinator from raw data processing and reducing centralized data collection, the framework reduces communication overhead and computational cost.

The system was evaluated on a structured 120-case benchmark that reflects realistic and evolving multi-stage attack scenarios. Experimental results show a success rate of 0.94, outperforming strong single-model baselines such as GPT-5, which achieved a success rate of 0.87. The framework achieved an average latency of 2.97 seconds and consumed 805.65 tokens per query, while GPT-5 required 15.53 seconds and 1535.58 tokens under identical conditions. This corresponds to an 81% reduction in latency and a 48% reduction in token consumption.

These results show that structured multi-agent collaboration improves analysis reliability while reducing computational cost, making the framework suitable for real-world cybersecurity environments.

## System Architecture

### 3-Node Multi-Agent Layout

```
┌─────────────────┐
│  Master Node    │  ← Llama-PcapLog–based orchestrator
└────────┬────────┘
         │ Redis Pub/Sub
    ┌────┴────┐
    │         │
┌───▼───┐ ┌───▼───┐
│Packet │ │  Log  │  ← Llama-PcapLog–based workers
│Worker │ │Worker │
└───────┘ └───────┘
```

1. **Master Node**: Orchestrates analysis and produces the final verdict.
2. **Packet Worker**: Analyzes network packets (via tshark).
3. **Log Worker**: Analyzes system logs (via grep).

### Communication

- **Redis Pub/Sub**: Asynchronous messaging between nodes.
- **Topic-based routing**: `packet_analysis`, `log_analysis`, `master_aggregation`.

## Experiment Setup

The project compares three architectures:

1. **CMAF (Multi-Agent System)**: Distributed agents powered by Llama-PcapLog.
2. **SA (Single Agent)**: One LLM analyzing all data in a single flow.
3. **Rule-based (Centralized)**: Traditional Snort-style rule-based detection.

## Requirements

### Required Software

- Python 3.11+
- Docker & Docker Compose
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- tshark (Wireshark CLI)
- Ollama (for running local LLMs)


### Environment Variables

Create a `.env` file and set API keys as needed:

```bash
# OpenAI (optional – for SA comparison)
OPENAI_API_KEY=sk-...

# Google Gemini (optional – for SA comparison)
GOOGLE_API_KEY=...

# Ollama host (Docker)
OLLAMA_HOST=http://host.docker.internal:11434

# MAS agent model
MAS_LLM_BACKEND=ollama
MAS_LLM_MODEL=Llama-PcapLog-Tool
```

## Installation and Running

### 1. Local Development

```bash
# Install dependencies
uv sync

# Generate dataset (once)
./run.sh create-dataset

# Start web interface
./run.sh app

# Open in browser
open http://localhost:8000
```

### 2. Docker (Multi-Agent)

```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f master
docker-compose logs -f packet-agent
docker-compose logs -f log-agent

# Stop
docker-compose down
```

### 3. Experiments

```bash
# 3-way comparison (3 iterations)
./run.sh experiment

# Model comparison (CMAF + SA models)
./run.sh experiment-by-model

# Visualize
./run.sh plot-paper
./run.sh plot-by-model
```

## Project Structure

```
multi-agent-pcaplog/
├── src/
│   ├── main.py          # Entry point (role-based node execution)
│   ├── agents.py        # LLMProvider, MasterOrchestrator, LocalSecurityAgent
│   ├── bus.py           # LocalMessageBus, RedisMessageBus
│   ├── protocol.py      # Message protocol definitions
│   ├── tools.py         # tshark, grep, Snort-style rules
│   ├── experiment.py    # Experiment runs and metrics
│   └── app.py           # FastAPI web interface
├── scripts/
│   ├── create_threat_dataset.py  # Test dataset generation
│   ├── convert_pcap.py           # PCAP conversion
│   ├── plot_paper_figure.py      # Paper-style figures
│   └── plot_by_model.py          # Model performance charts
├── data/
│   └── CIC-IDS2017/              # Network intrusion dataset
├── results/                       # Experiment outputs
├── tests/                         # Tests
├── docker-compose.yml             # Docker multi-node setup
├── Dockerfile                     # Container image
└── run.sh                         # Run script
```

## Experiment Outputs

After running experiments, `results/` will contain:

- `experiment_by_model.csv`: Per-case data (Category, Model, SR, Latency, Tokens)
- `experiment_by_model_summary.csv`: Per-model summary
- `full_metrics_report.csv`: Architecture-level comparison
- `pubsub_messages.jsonl`: Pub/sub message log (when enabled)

### Metrics

- **SR (Success Rate)**: Classification accuracy
- **Latency**: Response time (seconds)
- **Tokens**: Token usage

## Usage Examples

### Web Interface

Query example:

```
Analyze traffic for 192.168.10.50
```

The system will:

1. Have the Master plan the analysis
2. Assign work to Packet and Log workers in parallel
3. Run Llama-PcapLog in each worker
4. Aggregate results and output the final verdict

### Programmatic

```python
from src.agents import ToolEnabledAgent

agent = ToolEnabledAgent()
result = await agent.ask("Analyze suspicious activity from 192.168.10.50")
print(result["answer"])
```

## Development

### Adding a New Worker

1. Define a new `TaskType` in `src/protocol.py`
2. Implement the worker in `src/agents.py`
3. Add a service in `docker-compose.yml`
4. Extend role handling in `src/main.py`

### Adding Custom Tools

Add new tool functions in `src/tools.py` and call them from `LocalSecurityAgent`.

## Troubleshooting

### Ollama Connection Errors

```bash
# Check Ollama server
curl http://localhost:11434/api/tags

# From Docker to host Ollama
docker run --rm curlimages/curl:latest curl http://host.docker.internal:11434/api/tags
```

### Redis Connection Errors

```bash
# Check Redis container
docker-compose ps redis

# Test Redis
docker-compose exec redis redis-cli ping
```

### tshark Permission Errors

```bash
# Test tshark inside container
docker-compose exec packet-agent tshark --version
```

## Reproducibility Guide

This section provides detailed information for reproducing the experiments
and results described in the paper:
**"A Collaborative Multi-Agent Framework for Network Packets and System Logs Analysis"**

### Model Training Details (Llama-PcapLog Fine-tuning)

| Parameter | Value |
|---|---|
| **Base Model** | Meta-Llama-3-8B (8B parameters) |
| **Fine-tuning Method** | QLoRA (4-bit quantization + LoRA) |
| **LoRA Rank (r)** | 64 |
| **LoRA Alpha (α)** | 16 |
| **LoRA Dropout** | 0 |
| **LoRA Target Modules** | q_proj, k_proj, v_proj, o_proj, gate_proj, down_proj, up_proj |
| **Quantization** | 4-bit NF4 (BitsAndBytes) |
| **Max Sequence Length** | 2048 tokens |
| **Optimizer** | AdamW (torch) |
| **Learning Rate** | 2e-4 |
| **LR Scheduler** | Cosine annealing |
| **Warmup Ratio** | 0.1 |
| **Training Epochs** | 3 |
| **Batch Size** | 2 (per device) |
| **Gradient Accumulation Steps** | 4 (effective batch size = 8) |
| **Max Gradient Norm** | 0.3 |
| **Precision** | FP16 (mixed precision) |
| **Gradient Checkpointing** | Enabled |
| **Train/Validation Split** | 20% / 80% |

#### Training Dataset

The fine-tuning dataset is constructed from two sources:
1. **PCAP data** — Processed via `PcapProcessor` from raw packet captures (CIC-IDS2017).
2. **Syslog data** — Processed via `SyslogProcessor` from system log files.

Each sample follows the **Alpaca instruction format**:
```
### Instruction:
{question about the data}

### Input:
{structured packet/log data}

### Response:
{analysis answer}
```

Additional diverse tasks (Q&A, code generation, expert analysis) are generated
via a **Self-Instruct** strategy using GPT-4o-mini.

### Inference Configuration

| Parameter | Value |
|---|---|
| **Inference Framework** | Ollama (v0.5+) |
| **Model Format** | GGUF (quantized from merged LoRA + base model) |
| **Temperature** | default (via Ollama) |
| **Top-K / Top-P** | default |
| **Max Context** | 2048 tokens |
| **Serving** | OpenAI-compatible API (`/v1/chat/completions`) |

### Hardware & Software Environment

| Component | Specification |
|---|---|
| **Training GPU** | NVIDIA A100 80GB / RTX 4090 24GB |
| **Inference GPU** | NVIDIA RTX 3090 24GB (or CPU-only via Ollama) |
| **CPU** | AMD Ryzen 9 / Intel Xeon |
| **RAM** | 64GB+ |
| **OS** | Ubuntu 22.04 LTS |
| **Python** | 3.11+ |
| **PyTorch** | 2.10+ |
| **Transformers** | 5.1+ |
| **PEFT** | Latest (LoRA support) |
| **BitsAndBytes** | Latest (4-bit quantization) |
| **Ollama** | 0.5+ |
| **Docker** | 24+ with Compose v2 |
| **Redis** | 7+ (Alpine) |

### Evaluation Metrics

| Metric | Description | Formula |
|---|---|---|
| **Success Rate (SR)** | Classification accuracy | `SR = Correct / Total` |
| **Latency** | Average wall-clock analysis time | Per-query end-to-end seconds |
| **Tokens/Query** | LLM token consumption | Sum of all agent + coordinator tokens |
| **F1 Score** | Extraction quality (Llama-PcapLog eval) | Harmonic mean of Precision & Recall |
| **Pass@k** | Code generation correctness | Fraction of k samples with correct output |

### Structured Data Schema (Agent ↔ Coordinator Communication)

Each agent returns an `AgentIntelligence` JSON object to the coordinator:

```json
{
    "task_id": "a1b2c3d4-...",
    "agent_domain": "packet_analysis",
    "verdict": "Malicious",
    "confidence": 0.92,
    "evidence_summary": "Detected SYN flood pattern...",
    "detected_patterns": ["DoS", "SYN Flood"],
    "tool_calls": [
        {
            "tool_name": "tshark",
            "arguments": {"filter": "ip.addr == 172.16.0.1"},
            "is_valid_syntax": true,
            "is_correct_selection": true,
            "execution_success": true,
            "output_preview": "0.000 172.16.0.1 -> 192.168.10.50 ..."
        }
    ],
    "extracted_entities": ["172.16.0.1"],
    "processing_latency": 1.23,
    "tokens_consumed": 256
}
```

### Confidence-Weighted Aggregation Formula

The Master Coordinator aggregates agent reports using a two-stage approach:

1. **Confidence Calibration** per agent `i`:
   - Multi-Signal calculation: `c_i = min(0.50 + 0.15*S_tool + 0.15*S_ground + 0.10*S_pattern + 0.09*S_certain, 0.99)`
   - Where signals depend on tool success, entity grounding, detected patterns, and explicit verdict without hedging.

2. **Weighted Majority Vote**:
   ```
   S_mal = Σ c_i  for all agents with verdict = "Malicious"
   S_ben = Σ c_i  for all agents with verdict = "Benign"
   N_mal = count of "Malicious" verdicts
   N_ben = count of "Benign" verdicts

   if N_mal > N_ben:      final = "Malicious"   (majority wins)
   elif N_ben > N_mal:    final = "Benign"       (majority wins)
   else (tie):            final = argmax(S_mal, S_ben)  (confidence tiebreak)
   ```

### Synthetic Syslog Generation

The test benchmark uses synthetic syslog data generated from CIC-IDS2017 flow metadata:

1. **Input**: CIC-IDS2017 CSV fields (Source IP, Dest IP, Port, Duration, Packet counts, Label).
2. **Generation**: GPT-5 generates free-form Linux syslog lines (no fixed template).
3. **Data Leakage Prevention**: Ground-truth labels (e.g., "FTP-Patator", "DDoS") are
   **NOT embedded** in the syslog text. Instead, the LLM produces naturalistic log entries
   (e.g., "Failed password for root from 192.168.10.50", "SYN flood detected from 172.16.0.1").
4. **Validation**: Run `python scripts/validate_data_leakage.py` to verify.

### Scalability Architecture

The system supports horizontal scaling via Redis Pub/Sub:

```
                    ┌─────────────┐
                    │   Redis     │
                    │  Pub/Sub    │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌───▼────┐ ┌────▼─────┐
        │  Packet    │ │  Log   │ │ Packet   │  ← Scale-out
        │  Agent #1  │ │ Agent  │ │ Agent #2 │
        └────────────┘ └────────┘ └──────────┘
```

To add more agents:
1. Start additional Docker containers with the same `AGENT_ROLE`
2. Each agent auto-registers via the `AGENT_REGISTER` topic
3. The coordinator dispatches work to all registered agents
4. Results are collected via `MASTER_AGGREGATION` with timeout-based fault tolerance

### Validation & Analysis Scripts

```bash
# Validate no data leakage in synthetic syslog
python scripts/validate_data_leakage.py

# Classify hallucinations (Critical vs Benign)
python scripts/analyze_hallucination.py

# RTT-corrected latency comparison
python scripts/analyze_latency_rtt.py --measure-rtt
```

## References
- CIC-IDS2017 Dataset: https://www.unb.ca/cic/datasets/ids-2017.html
- Llama-PcapLog (GitHub): https://github.com/choihyuunmin/Llama-PcapLog
- Llama-PcapLog (HuggingFace): https://huggingface.co/CNU-CHOI/Llama-PcapLog
