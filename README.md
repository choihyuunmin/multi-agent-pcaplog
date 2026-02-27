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

## License

MIT License

## References

- CIC-IDS2017 Dataset: https://www.unb.ca/cic/datasets/ids-2017.html
- Llama-PcapLog: (paper or model link)
