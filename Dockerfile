# Dockerfile
FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y 
    tshark 
    iputils-ping 
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY src/ ./src/
COPY data/ ./data/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

RUN groupadd -f wireshark && usermod -a -G wireshark root

CMD ["uv", "run", "python", "-m", "src.main"]
