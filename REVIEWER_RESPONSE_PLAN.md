## Reviewer A 지적 사항 및 처리 방안

1. 합성 로그 생성 방법론에 대한 설명 부족
- 리뷰어 원본 코멘트 : "Synthetic log generation methodology is insufficiently described... no technical detail is given on how this was done: what generator was used, what statistical properties were matched, what the label alignment procedure was, and whether the synthesis could introduce data leakage (e.g., attack labels embedded in log content)... A dedicated subsection or appendix with the generation methodology, validation against realistic syslog distributions, and an analysis of potential biases is required."

- 처리 방안 : scripts/create_threat_dataset.py 코드를 참조하여 생성 과정 섹션을 추가합니다.
  - 해당 스크립트는 GPT-5를 활용하여 CIC-IDS2017의 메타데이터(IP, 포트, 지속시간, 패킷 수 등)를 컨텍스트로 제공하고, 고정된 템플릿 없이 리눅스 syslog를 생성하도록 유도합니다.s
  - 실험 설정(Experimental Setup) 부분에 데이터 편향성 방지 및 데이터 누수(Data leakage) 방지 처리 과정을 구체적으로 명시합니다.
- 대상 섹션 : 4.experiments -> subsection{Experimental Setup}


2. 높은 환각(Hallucination) 비율(31%)에 대한 설명 및 정당성 부족
- 리뷰어 원본 코멘트 : "Hallucination rate of 0.31 is unexplained and potentially concerning... This assertion must be substantiated: (a) provide the definition and measurement methodology for the hallucination metric; (b) give concrete examples distinguishing hallucinated text from correct conclusions; (c) explain why a 31% hallucination rate does not affect downstream classification correctness; and (d) discuss whether this poses a risk in adversarial conditions or edge cases."

- 처리 방안 : scripts/analyze_hallucination.py 분석 결과를 기반으로 구체적인 표와 통계를 제시합니다.
  - 논문에 제시된 환각률은 위험 패킷을 정확히 분류하지 못했다는 내용이 아닌, LLM이 답변을 생성할 때 발생하는 부가적인 정보(문장 생성, 예시 제공 등)에 대한 환각임을 명시합니다.
  - 무해한 환각이 최종 예측에 악영향을 주지 않음을 입증하는 수치를 제시하고, 다중 에이전트 합의 메커니즘이 노이즈를 필터링하는 원리를 추가 설명합니다.
- 대상 섹션 : 4.experiments -> subsubsection{Agent Reasoning Stability and Reliability} 및 5.discussion


3. 공정한 지연 시간(Latency) 비교를 위한 베이스라인 부재
- 리뷰어 원본 코멘트 : "Absence of a shared-infrastructure baseline limits the latency comparison... If GPT-5 is API-based, the latency differential may primarily reflect network conditions rather than algorithmic efficiency. A fair comparison requires deploying a monolithic LLM locally (e.g., Llama-3 70B) under identical infrastructure, or explicitly reporting and accounting for API round-trip time in the analysis."
- 처리 방안 : scripts/analyze_latency_rtt.py의 측정 결과를 바탕으로 내용을 수정합니다.
  - 클라우드 API 모델(GPT-5, Gemini-3)의 전체 지연 시간 중 네트워크 RTT가 차지하는 비율을 명시합니다.
  - 단일 에이전트 대비 다중 에이전트 시스템의 속도 향상이 네트워크 지연 때문이 아닌, 병렬 처리 및 분산 추론 구조 자체의 효율성 덕분임을 객관적 수치로 증명합니다.
- 대상 섹션 : 4.experiments -> subsubsection{Inference Latency and Token Efficiency}


4. 고부하(High-load) 환경에서의 확장성 검증 부족
- 리뷰어 원본 코멘트 : "1. The authors should clarify and evaluate how the system’s performance degrades under high-volume, concurrent attack scenarios beyond the current testbed scale (i.e., more than one Coordinator and two agent servers)."

- 처리 방안 : 제안 프레임워크가 Redis Pub/Sub 기반의 비동기 이벤트 큐 시스템을 채택하고 있음을 강조합니다.
  - 에이전트의 동적 등록(TaskType.AGENT_REGISTER) 및 해제가 가능하여 대규모 트래픽 발생 시 부하 분산이 용이한 구조적 장점을 논문에 보완합니다.
- 대상 섹션 : 3.proposed -> subsection{Overview} 및 5.discussion


5. 신뢰도 기반 가중치 집계(Confidence-weighted aggregation) 설명 부족
- 리뷰어 원본 코멘트 : "2. The authors should provide a clear explanation of the “confidence-weighted aggregation” mechanism, including how per-agent confidence scores are calibrated. If calibration methods are used, the authors should include an analysis or experimental validation of their effectiveness."

- 처리 방안 : 기존의 토큰 수 기반 집계 방식을 폐기하고, src/agents.py에 다중 신호 기반 신뢰도 산출 로직을 구현하여 논문에 수식화합니다.
  - "에이전트가 실제 증거를 갖고 있는가?"를 정량화하기 위해 설계했습니다. 실제 데이터 없이 추측만 하는 에이전트의 신뢰도는 낮아야 하고, 도구가 성공적으로 데이터를 수집하고 구체적 패턴까지 탐지한 에이전트의 신뢰도는 높아야 합니다.
  - 공식 : c_i = 0.50 + 0.15·S_tool + 0.15·S_ground + 0.10·S_pattern + 0.09·S_certain
    - S_tool : 도구 실행 결과에 "Error"가 없고 비어있지 않으면 1 
    - S_ground : 타겟 IP 문자열이 도구 출력에 포함되면 1
    - S_pattern : 구체적 공격 패턴(DoS, BruteForce, PortScan)이 매칭되면 1
    - S_certain: 응답에 "verdict:" 태그가 존재
  - 모든 신호가 충족되면 0.99, 아무것도 없으면 0.50으로 신뢰도가 결정됩니다.
- 대상 섹션 : 3.proposed -> subsection{Coordinator}


6. Llama-PcapLog 모델의 재현성 및 접근성
- 리뷰어 원본 코멘트 : "3. The authors should clarify the availability of Llama-PcapLog. If it is publicly available, the access information should be provided; otherwise, sufficient implementation details and performance characteristics must be described to ensure reproducibility."

- 처리 방안 : src/agents.py에 구현된 LLMProvider의 다중 백엔드 지원(Ollama, Gemini, OpenAI)을 언급하며, 로컬 환경에서 Ollama를 통해 재현 가능함을 명시합니다. 사용한 모델의 GitHub 링크와 Huggingface 모델 링크를 제시합니다.
- 대상 섹션 : 4.experiments -> subsection{Experimental Setup}


7. 제로데이 공격(Zero-day attacks) 대응 논리 부족
- 리뷰어 원본 코멘트 : "4. The authors should elaborate on how the proposed framework handles zero-day attacks that generate minimal or ambiguous log and packet evidence, supported by either experimental results or a detailed methodological discussion."

- 처리 방안 : 공격 탐지와 신뢰도 산출의 작동 방식을 명확히 분리하여 논문을 보강합니다:
  - 탐지 : 최종 판정은 사전에 정의된 시그니처나 키워드 룰에 의존하지 않고, LLM이 문맥 기반으로 이상 징후와 공격 의도를 추론하므로 제로데이 공격도 탐지할 수 있습니다.
  - 신뢰도 산출의 합리성 : 신뢰도 공식의 S_pattern은 알려진 패턴(시그니처)이 확인될 때 추가 확신(+0.10)을 주는 보조 신호입니다. 제로데이 공격의 경우 알려진 패턴이 없으므로 S_pattern=0이 되어 신뢰도가 0.99가 아닌 0.89로 산출됩니다. 이는 과거에 알려진 명확한 공격 패턴이 보이지 않을 때는 100% 확신하지 않고 다소 보수적인 신뢰도를 산출한다는 시스템 설계임을 안내합니다.
- 대상 섹션 : 4.experiments -> subsubsection{Adaptability to Latest Threats}


---


## Reviewer B 지적 사항 및 처리 방안

1. 구조화된 데이터(Structured Data) 스키마 설명 부족
- 리뷰어 원본 코멘트 : "1. Lack of Explanation of Structured Data. The manuscript does not provide a clear or detailed description of the structured data format used for communication between the agent and the coordinator... explicitly define: -The data schema or format -The fields and their semantics -How the data is generated, parsed, and consumed"

- 처리 방안 : src/protocol.py의 Pydantic 스키마 정의를 기반으로 데이터 포맷 표를 논문에 삽입합니다.
  - protocol.py 내의 데이터 포맷 객체의 JSON 직렬화 구조를 보여주고, 각 필드(verdict, confidence, evidence_summary 등)의 역할과 데이터 타입을 명확히 정의합니다.
- 대상 섹션 : 3.proposed -> subsection{Agent Communication Protocol}


2. 워크플로우 및 시스템 제어 흐름(Control Flow) 설명 부족
- 리뷰어 원본 코멘트 : "2. Insufficient Description of the Proposed Mechanism. The paper lacks a detailed explanation of how the agent-coordinator architecture operates. The workflow, control flow, and interaction logic are not described with enough specificity."

- 처리 방안 :  동작 기반의 상태 다이어그램으로 시각화합니다. 
    1) 의도 추출 -> 2) 타겟 도메인 증거 수집 -> 3) 보고서 대기 -> 4) 신뢰도 가중치 기반 최종 종합 과정을 명시합니다.
- 대상 섹션 : 3.proposed -> subsection{Coordinator}


3. 모델 학습(Training)에 대한 세부 정보 누락
- 리뷰어 원본 코멘트 : "3. Missing Details on AI Model Training. The manuscript does not describe the AI models used for training, nor the input/output parameters involved... specify: -Model architectures -Training datasets -Input feature representations -Output formats -Hyperparameters and training conditions"

- 처리 방안 : 별도의 학습 설정 내용(Experimental Setup 내부에 서브섹션)을 구성하여 Llama-PcapLog 학습 내용을 베이스 모델, 파인튜닝 기법, 에포크(Epoch), 러닝 레이트(Learning Rate), 배치 사이즈 및 QCA 데이터셋 규모를 명시합니다.
- 대상 섹션 : 4.experiments -> subsection{Experimental Setup}


4. 모델 추론(Inference) 세부 정보 누락
- 리뷰어 원본 코멘트 : "3. Missing Details on AI Model Inference. Similarly, the inference process is not described. The authors should clearly state: -The inference-time model configuration -Input/output formats -Any post-processing or decision logic applied"

- 처리 방안 : src/agents.py의 후처리 로직을 구체적으로 설명합니다. LLM 응답에서 최종 판정을 추출하는 과정은 다음 2단계로 이루어집니다:
  1. 명시적 태그 우선 파싱: LLM 응답에서 VERDICT: Malicious 또는 VERDICT: Benign 태그를 먼저 찾아 판정합니다.
  2. 부정어 필터링 (Fallback): 태그가 없을 경우, 응답에 "malicious"라는 단어가 있더라도 "no attack", "not malicious" 등의 부정 문맥이 함께 있으면 이를 공격이 아닌 것으로 올바르게 처리합니다. (예: "There is no malicious activity" → Benign으로 판정)
- 대상 섹션 : 3.proposed -> subsection{Network Analysis Agent}


5. 모델 수렴도(Convergence) 평가 과정 부재
- 리뷰어 원본 코멘트 : "4. No Information on Convergence Evaluation. The paper does not provide information on how the convergence of the AI models was evaluated during training. This includes: -Convergence criteria -Loss curves or metrics -Validation procedures"

- 처리 방안 : 3번 처리방안과 같습니다. Llama-PcapLog는 이전 논문에서 파인튜닝된 모델을 가져다 사용한 것이며, 학습 관련 내용을 Llama-PcapLog의 수치를 사용합니다.
- 대상 섹션 : 4.experiments -> subsection{Experimental Setup} 내에서 모델 출처 명시


6. 추론 평가 환경(Evaluation Conditions) 정보 부족
- 리뷰어 원본 코멘트 : "5. No Description of Inference Evaluation Conditions. The conditions under which inference was evaluated are not described. The authors must clarify: -Evaluation datasets -Metrics used -Experimental settings -Hardware/software environment"

- 처리 방안 : Docker 컨테이너 환경이라는 점 외에, 추론 테스트에 사용된 GPU 하드웨어 스펙, 소프트웨어 환경, API 모델 호출 조건 등을 상세히 명시하여 완전한 재현이 가능하도록 보완합니다.
- 대상 섹션 : 4.experiments -> subsection{Experimental Setup}