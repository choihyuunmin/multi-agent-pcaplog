# Llama-PcapLog와 멀티에이전트 패킷·로그 분석

Llama를 패킷과 시스템 로그 분석에 맞게 파인튜닝하고, 해당 모델을 두 분석
에이전트에서 사용하는 프로젝트입니다. 모델 성능을 먼저 평가한 뒤, 패킷과 로그를
각각 조회하고 결과를 합치는 시스템의 성능을 평가합니다.

## 준비

- Python 3.11, Poetry, uv
- 모델 학습용 NVIDIA GPU와 CUDA
- 시스템 평가용 Ollama와 `tshark`
- Llama 모델 사용 권한과 Hugging Face 계정

```bash
git clone https://github.com/choihyuunmin/multi-agent-pcaplog.git
cd multi-agent-pcaplog
```

모델 학습·평가는 `llama-pcaplog/`, 멀티에이전트 실행·평가는 저장소 최상위
폴더에서 진행합니다. 두 프로젝트는 의존성이 달라 환경을 따로 설치합니다.

## 1. Llama 파인튜닝

패킷과 시스템 로그를 질문·입력·응답 형태로 준비하고 Llama 3 8B를 LoRA로
파인튜닝합니다. 학습 자료와 전처리 코드는 `llama-pcaplog/model/`에 있습니다.

```bash
cd llama-pcaplog
poetry env use python3.11
poetry install
poetry run python -m pip install peft bitsandbytes datasets
poetry run python -c "from huggingface_hub import login; login()"
```

아래 `your-hf-username`을 본인 Hugging Face 계정으로 바꿉니다.
학습 스크립트는 학습 결과를 저장하고 병합 모델을 Hugging Face에 업로드합니다.

```bash
poetry run python model/training/train_model.py \
  --model-name meta-llama/Meta-Llama-3-8B \
  --dataset-dir model/datasets \
  --output-dir outputs \
  --hf-model-name your-hf-username/Llama-PcapLog
```

## 2. 모델 평가

기본 분석, 고급 분석, 취약점 분류, 코드 생성 과제를 평가합니다.
파인튜닝 모델과 기본 Llama를 포함한 비교 모델을 순서대로 실행하며,
정보 추출 점수, 코드 과제 통과 수, 응답시간 등을 저장합니다.

`llama-pcaplog/`에서 실행합니다.

```bash
poetry run python evaluation/run_benchmark.py \
  --benchmark_dir evaluation \
  --output_dir evaluation/results
```

질문과 정답은 `evaluation/test/test_dataset.json`, 평가 결과는
`evaluation/results/`에 저장됩니다. 코드 생성 과제는 평가 스크립트에 포함돼
있습니다. 평가할 모델 목록은 `evaluation/run_benchmark.py`의 `model_configs`에서
확인할 수 있습니다. 방금 학습한 모델을 평가하려면 목록의 Llama-PcapLog 경로를
학습 때 지정한 Hugging Face 저장소로 바꿉니다. `OPENAI_API_KEY`가 설정돼 있으면
GPT-4o도 함께 평가합니다.

## 3. 두 에이전트 구성

패킷 에이전트는 `tshark`로 패킷을 조회하고, 로그 에이전트는 `grep`으로 시스템
로그를 조회합니다. 두 에이전트는 각 자료를 분석한 결과와 근거를 반환합니다.
조정기는 질문을 나눠 전달하고, 두 결과를 합쳐 최종 판단을 만듭니다.

```text
사용자 질문
    ↓
조정기
    ├── 패킷 에이전트: PCAP 조회와 분석
    └── 로그 에이전트: 시스템 로그 조회와 분석
    ↓
결과 결합과 최종 응답
```

저장소 최상위 폴더로 돌아와 설치합니다.

```bash
cd ..
uv sync
cp .env.example .env
ollama list
```

파인튜닝 모델을 Ollama에 등록하고, `.env`를 아래처럼 수정합니다.
`MAS_LLM_MODEL`에는 `ollama list`에 표시되는 실제 모델 이름을 넣습니다.
학습 결과가 Ollama에 자동으로 등록되지는 않습니다.

```dotenv
OPENAI_API_KEY=
GOOGLE_API_KEY=
OLLAMA_HOST=http://localhost:11434
MAS_LLM_BACKEND=ollama
MAS_LLM_MODEL=Llama-PcapLog-tool:latest
REDIS_HOST=
REDIS_PORT=6379
PUBSUB_LOG_PATH=results/pubsub_messages.jsonl
```

별도 터미널에서 `ollama serve`를 실행합니다. 이미 실행 중이면 다시 켤 필요는
없습니다. 로컬 실행에서는 Redis 없이 두 에이전트가 메모리 내 메시지를 주고받습니다.

## 4. 시스템 평가

멀티에이전트, 단일 에이전트, 규칙 기반 분석을 비교합니다. 같은 질문에 대한
판단 성공률, 응답시간, 토큰 사용량을 측정합니다.

실험 전 아래 파일을 준비합니다.

| 파일 | 용도 |
| --- | --- |
| `data/CIC-IDS2017/Tuesday-WorkingHours.pcap` | 패킷 조회 |
| `data/CIC-IDS2017/syslog_threats.log` | 시스템 로그 조회 |
| `results/qca_test_dataset_100.json` | 평가 질문과 정답 |

로그 파일이 없으면 코드가 `data/CIC-IDS2017/Tuesday-WorkingHours_converted.csv`를
대신 사용합니다. 평가 질문은 저장소에 포함돼 있습니다. 직접 자료를 생성하려면
CIC-IDS2017 CSV를 `data/*.pcap_ISCX.csv`에 두고 `./run.sh create-dataset`을
실행합니다. 생성된 로그는 합성 로그입니다.

저장소 최상위 폴더에서 실행합니다.

```bash
./run.sh experiment
```

기본 실험은 3회 반복합니다. 멀티에이전트는 `.env`의 Ollama 설정을 사용합니다.
단일 에이전트 비교 경로는 `OPENAI_API_KEY`를 사용하며, 키가 없으면 규칙 기반
대체 응답을 사용합니다. 실제 LLM 성능을 비교할 때는 키와 호출 성공 로그를
확인해야 합니다.

| 결과 파일 | 내용 |
| --- | --- |
| `results/final_experiment_results.csv` | 질문별 결과 |
| `results/full_metrics_report.csv` | 방식별 평가 지표 |
| `results/final_statistical_metrics.csv` | 반복 실험 요약 |
| `results/pubsub_messages.jsonl` | 에이전트 메시지 기록 |

### 웹 화면 확인

```bash
./run.sh app
```

`http://localhost:8000`에서 `Analyze traffic for 192.168.10.50`처럼 질문합니다.
현재 웹 화면은 `MAS_LLM_MODEL` 대신 별도의 자동 선택 경로를 사용합니다.
`OPENAI_API_KEY`가 있으면 OpenAI를 호출하고, 없거나 호출에 실패하면 규칙 기반
대체 응답을 사용합니다. 로컬 모델을 이용한 성능 평가는 위 실험 명령으로 진행합니다.

## 코드 위치

| 위치 | 내용 |
| --- | --- |
| [llama-pcaplog/model/](llama-pcaplog/model/) | 데이터 전처리와 파인튜닝 |
| [llama-pcaplog/evaluation/](llama-pcaplog/evaluation/) | 모델 평가 |
| [src/agents.py](src/agents.py) | 두 에이전트와 조정기 |
| [src/tools.py](src/tools.py) | 패킷·로그 조회 도구 |
| [src/experiment.py](src/experiment.py) | 시스템 평가 |
| [results/](results/) | 평가 결과와 [데모 영상](results/demo/demo.mp4) |

모델 개발 코드는 [원본 저장소](https://github.com/choihyuunmin/llama-syslog-packet)에서
가져왔으며, 기존 커밋과 메시지를 그대로 유지했습니다.
