# multi-agent-pcaplog

Collaborative multi-agent security analysis for network packets and system
logs. A coordinator sends structured tasks to packet and log agents, receives
structured evidence reports, and produces a final verdict.

## Demo Video

<video src="results/demo/demo.mp4" controls width="100%">
  Your browser does not support the video tag.
</video>

[Demo video](results/demo/demo.mp4)

For a short setup path, start with [QUICKSTART.md](QUICKSTART.md).

## What This Project Does

The project demonstrates a multi-agent security-analysis workflow:

1. A user asks a security question, usually with a target IP address.
2. The coordinator extracts the target and decides which agents are needed.
3. The packet agent inspects PCAP evidence with `tshark`.
4. The log agent inspects host or syslog evidence with `grep`.
5. Each agent returns a structured report with verdict, confidence, evidence,
   tool metadata, and latency.
6. The coordinator combines the reports with majority voting and confidence
   tie-breaking.

The paper version evaluates this design on a 120-case benchmark and compares it
with single-agent and rule-based baselines.

## Architecture

```text
User query
   |
   v
Coordinator
   | publishes JSON tasks
   v
Message bus
   |--------------------|
   v                    v
Packet agent        Log agent
PCAP/tshark         syslog/grep
   |                    |
   | structured reports |
   v                    v
Coordinator aggregation
   |
   v
Final verdict and explanation
```

Two message buses are supported:

- Local in-memory bus for the web app, tests, and simple experiments.
- Redis Pub/Sub for Docker Compose multi-container runs.

## Requirements

Required for local development:

- Python 3.11+
- `uv`

Recommended:

- `tshark` from Wireshark for real packet inspection
- Ollama for local LLM inference
- Docker Desktop for the Redis-backed multi-container demo

Install example on macOS:

```bash
brew install uv wireshark
```

Optional Ollama setup:

```bash
brew install ollama
ollama serve
ollama pull llama3:8b
```

## First Run

```bash
git clone https://github.com/choihyuunmin/multi-agent-pcaplog.git
cd multi-agent-pcaplog
uv sync
cp .env.example .env
./run.sh test
./run.sh app
```

Open:

```text
http://localhost:8000
```

Try:

```text
Analyze traffic for 192.168.10.50
```

No API key is required for this smoke test. If no model backend is available,
the system uses a small rule-based fallback so the flow can still be checked.

## Environment Configuration

For local runs, keep Redis disabled:

```env
REDIS_HOST=
REDIS_PORT=6379
```

For local Ollama:

```env
OLLAMA_HOST=http://localhost:11434
MAS_LLM_BACKEND=ollama
MAS_LLM_MODEL=llama3:8b
```

For the paper model, set:

```env
MAS_LLM_MODEL=Llama-PcapLog-Tool
```

OpenAI and Gemini keys are optional and are mainly used for single-agent
comparison experiments:

```env
OPENAI_API_KEY=
GOOGLE_API_KEY=
```

Do not put real API keys in committed files.

## Main Commands

```bash
./run.sh test
./run.sh app
./run.sh docker-up
./run.sh docker-logs
./run.sh docker-down
./run.sh experiment
./run.sh experiment-by-model
./run.sh plot-paper
./run.sh plot-by-model
./run.sh validate-leakage
./run.sh analyze-hallucination
./run.sh analyze-rtt
```

### Local Web App

```bash
./run.sh app
```

The local web app creates the coordinator, packet agent, and log agent in one
Python process. This is the easiest way to verify the workflow.

### Docker Multi-Agent Demo

```bash
./run.sh docker-up
```

Docker Compose starts:

- `redis`
- `packet-agent`
- `log-agent`
- `master`

The Docker services set `REDIS_HOST=redis` internally. Local non-Docker runs
should leave `REDIS_HOST` empty.

### Experiments

Run the architecture comparison:

```bash
./run.sh experiment
```

Run the model comparison:

```bash
./run.sh experiment-by-model
```

Generate figures:

```bash
./run.sh plot-paper
./run.sh plot-by-model
```

## Outputs

Experiment outputs are written under `results/`.

Common files:

```text
results/final_experiment_results.csv
results/full_metrics_report.csv
results/final_statistical_metrics.csv
results/experiment_by_model.csv
results/experiment_by_model_summary.csv
results/pubsub_messages.jsonl
```

Figures are written under:

```text
results/figures/
```

## Project Structure

```text
multi-agent-pcaplog/
├── src/
│   ├── app.py          # FastAPI web interface
│   ├── agents.py       # Coordinator, local agents, LLM provider
│   ├── bus.py          # In-memory and Redis message buses
│   ├── experiment.py   # Benchmark runners
│   ├── main.py         # Role-based Docker entry point
│   ├── protocol.py     # Pydantic message schemas
│   └── tools.py        # tshark, grep, rule-based baseline tools
├── scripts/            # Dataset, validation, and plotting helpers
├── data/               # Local packet/log data
├── results/            # Benchmark outputs and generated figures
├── tests/              # Unit tests
├── docker-compose.yml
├── Dockerfile
├── run.sh
├── QUICKSTART.md
└── README.md
```

## Programmatic Use

```python
import asyncio
from src.agents import ToolEnabledAgent

async def main():
    agent = ToolEnabledAgent()
    result = await agent.ask("Analyze traffic for 192.168.10.50")
    print(result["answer"])
    for line in result["execution_log"]:
        print(line)

asyncio.run(main())
```

Run it from the repository root so relative data paths resolve correctly.

## Data Notes

The repository includes a small log file for smoke testing. For full
paper-style experiments, prepare the expected CIC-IDS2017-derived files under:

```text
data/CIC-IDS2017/
```

You can generate the synthetic test log and QCA-style dataset with:

```bash
./run.sh create-dataset
```

Validation helpers:

```bash
./run.sh validate-leakage
./run.sh analyze-hallucination
./run.sh analyze-rtt
```

## Troubleshooting

### Local App Cannot Connect to Redis

If you see an error about host `redis`, your local `.env` is using the Docker
Redis hostname.

Use this for local runs:

```env
REDIS_HOST=
```

Use Docker Compose for Redis-backed runs:

```bash
./run.sh docker-up
```

### Ollama Model Is Missing

```bash
ollama list
ollama pull llama3:8b
```

Then set:

```env
MAS_LLM_MODEL=llama3:8b
```

### `tshark` Is Missing

Install Wireshark/tshark:

```bash
brew install wireshark
```

The code returns a readable tool error if `tshark` is unavailable, but real PCAP
analysis requires it.

### Tests Fail Because Dependencies Are Missing

Run:

```bash
uv sync
./run.sh test
```

## Paper

This repository supports the experiments for:

**A Collaborative Multi-Agent Framework for Network Packets and System Logs Analysis**

The paper evaluates a coordinator-agent architecture that avoids sending all raw
packet and log data to a single large prompt. Instead, each agent extracts local
evidence and returns a compact structured report for aggregation.
