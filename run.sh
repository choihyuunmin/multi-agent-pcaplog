#!/bin/bash

export PYTHONPATH=$PYTHONPATH:$(pwd)

if [ -f ".env" ]; then
  export $(grep -v '^#' .env | xargs)
fi

case "$1" in
  "experiment")
    echo "Running Experiment (3-way comparison: CMAF vs SA vs Rule-based, 3 iterations)..."
    echo "  → results/final_experiment_results.csv"
    echo "  → results/full_metrics_report.csv"
    echo "  → results/final_statistical_metrics.csv"
    uv run python src/experiment.py
    ;;
  "experiment-by-model")
    echo "Running model comparison experiment (CMAF + SA models)..."
    echo "  → results/experiment_by_model.csv   (Category,Model,SR,Latency,Tokens)"
    echo "  → results/experiment_by_model_summary.csv"
    uv run python src/experiment.py by-model
    ;;
  "app")
    echo "Starting Web App..."
    uv run python src/app.py
    ;;
  "create-dataset")
    echo "Creating Dataset (threat packet + syslog)..."
    uv run python scripts/create_threat_dataset.py
    ;;
  "convert-pcap")
    echo "Converting PCAP..."
    uv run python scripts/convert_pcap.py
    ;;
  "plot-full-metrics")
    echo "Generating full metrics figure..."
    uv run python scripts/plot_full_metrics_figure.py
    ;;
  "plot-by-model")
    echo "Generating by-model figure..."
    uv run python scripts/plot_by_model.py
    ;;
  "docker-up")
    echo "Starting Docker multi-agent environment..."
    docker-compose up --build
    ;;
  "docker-down")
    echo "Stopping Docker environment..."
    docker-compose down
    ;;
  "docker-logs")
    echo "Showing Docker logs..."
    docker-compose logs -f
    ;;
  "test")
    echo "Running tests..."
    uv run pytest tests/ -v
    ;;
  *)
    echo "multi-agent-pcaplog - Multi-Agent Security Analysis System"
    echo ""
    echo "Usage: ./run.sh {command}"
    echo ""
    echo "Experiment Commands:"
    echo "  experiment          : CMAF vs SA vs Rule-based (3 iterations)"
    echo "                        → results/final_experiment_results.csv"
    echo "  experiment-by-model : CMAF + SA models comparison"
    echo "                        → results/experiment_by_model.csv"
    echo ""
    echo "Application Commands:"
    echo "  app                 : Start FastAPI web interface"
    echo ""
    echo "Docker Commands:"
    echo "  docker-up           : Start multi-agent Docker environment"
    echo "  docker-down         : Stop Docker environment"
    echo "  docker-logs         : View Docker container logs"
    echo ""
    echo "Data & Visualization:"
    echo "  create-dataset      : Generate QCA test dataset"
    echo "  convert-pcap        : Convert PCAP files to CSV"
    echo "  plot-paper          : Generate paper figure (PDF + PNG)"
    echo "  plot-full-metrics   : Generate full metrics figure"
    echo "  plot-by-model       : Chart by model comparison"
    echo ""
    echo "Utilities:"
    echo "  pubsub-log          : Regenerate pub/sub message log"
    echo "  test                : Run unit tests"
    ;;
esac
