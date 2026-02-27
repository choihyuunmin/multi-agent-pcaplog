# Quick Start Guide

## Get Started in 5 Minutes

### 1. Prerequisites

```bash
# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Ollama (macOS)
brew install ollama

# Start Ollama server
ollama serve
```

### 2. Project Setup

```bash
# Clone the repository
git clone <repository-url>
cd multi-agent-pcaplog

# Install dependencies
uv sync

# Configure environment variables
cp .env.example .env
# Edit .env to add API keys (optional)
```

### 3. Llama-PcapLog Model Setup

```bash
# Open a new terminal
# Option 1: If you have a pre-trained Llama-PcapLog model
ollama create Llama-PcapLog-Tool -f /path/to/Modelfile

# Option 2: Use a default model for testing
ollama pull llama3:8b
# In .env, set MAS_LLM_MODEL=llama3:8b
```

### 4. Data Preparation

```bash
# Generate the test dataset
./run.sh create-dataset
```

### 5. Run Options

#### A. Web Interface (Easiest)

```bash
./run.sh app
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

#### B. Docker Multi-Agent Environment

```bash
# Run in background
docker-compose up -d

# View logs
docker-compose logs -f master

# Stop
docker-compose down
```

#### C. Run Experiments

```bash
# 3-way comparison (CMAF vs SA vs Rule-based)
./run.sh experiment

# View results
cat results/full_metrics_report.csv
```

## Troubleshooting

### Ollama Connection Failed

```bash
# Check Ollama status
curl http://localhost:11434/api/tags

# List models
ollama list
```

### Docker Run Errors

```bash
# Check Redis status
docker-compose ps

# Restart containers
docker-compose restart
```

### Missing Data Files

```bash
# Download CIC-IDS2017 dataset
# https://www.unb.ca/cic/datasets/ids-2017.html

# Place PCAP and CSV files under data/CIC-IDS2017/
```

## Experiment Guide

### 1. Default Experiment (3 iterations)

```bash
./run.sh experiment
```

**Output files**:

- `results/final_experiment_results.csv`: Raw per-case data
- `results/full_metrics_report.csv`: Architecture-level summary
- `results/final_statistical_metrics.csv`: Statistical metrics

### 2. Model Comparison Experiment

```bash
./run.sh experiment-by-model
```

**Models compared**:

- CMAF (multi-agent): Llama-PcapLog-Tool
- SA: GPT-5, Gemini-3-Pro, Llama3, DeepSeek-R1, Qwen3

**Output files**:

- `results/experiment_by_model.csv`: Per-case results (Category, Model, SR, Latency, Tokens)
- `results/experiment_by_model_summary.csv`: Per-model summary

### 3. Visualize Results

```bash
# Paper-style charts
./run.sh plot-paper

# Model comparison charts
./run.sh plot-by-model
```

## Using the Web Interface

### 1. Start the Server

```bash
./run.sh app
```

### 2. Submit a Query

In the browser, enter for example:

```
Analyze traffic for 192.168.10.50
```

### 3. View Results

The system will:

1. Have the Master plan the analysis
2. Assign tasks to Packet and Log workers
3. Run analysis with Llama-PcapLog in each worker
4. Aggregate results and produce a final verdict in the Master

Execution logs and the final answer are shown on the page.

## Programmatic Usage

```python
import asyncio
from src.agents import ToolEnabledAgent

async def main():
    agent = ToolEnabledAgent()
    result = await agent.ask("Analyze suspicious activity from 192.168.10.50")
    print(result["answer"])
    print("\nExecution log:")
    for log in result["execution_log"]:
        print(f"  - {log}")

asyncio.run(main())
```

## Performance Tips

### 1. Ollama Settings

```bash
# Enable GPU (if NVIDIA GPU available)
export OLLAMA_GPU=1

# Limit loaded models
export OLLAMA_MAX_LOADED_MODELS=2
```

### 2. Redis Tuning

In `docker-compose.yml`:

```yaml
redis:
  command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
```

### 3. Iteration Count

Adjust `num_iterations` in the experiment script:

```python
# src/experiment.py
await run_final_repeated_experiment(num_iterations=5)
```

## Further Resources

- [CIC-IDS2017 Dataset](https://www.unb.ca/cic/datasets/ids-2017.html)
- [Ollama Documentation](https://github.com/ollama/ollama)
- [Redis Pub/Sub](https://redis.io/docs/interact/pubsub/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
