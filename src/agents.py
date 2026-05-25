import os
import re
import json
import uuid
import asyncio
import time
import logging

from typing import Dict, List, Any, Optional
from openai import OpenAI
import google.generativeai as genai

from src.protocol import AgentMessage, MessageHeader, TaskType, TaskParameter, AgentIntelligence, ToolCallInfo, SubGoalStatus, AgentRegistration
from src.bus import shared_bus
from src.tools import run_tshark, grep_system_logs, apply_snort_rules

logger = logging.getLogger(__name__)

class LLMProvider:
    def __init__(self, backend: str = "auto", model: Optional[str] = None):
        self.backend = backend
        self.model_name = model or "gpt-5"
        self.openai_client = None
        self.gemini_model = None
        self.total_tokens = 0

        if backend == "ollama":
            try:
                ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
                base_url = f"{ollama_host}/v1" if not ollama_host.endswith("/v1") else ollama_host
                self.openai_client = OpenAI(
                    base_url=base_url,
                    api_key="ollama",
                )
                self.model_name = model or "Llama-PcapLog-tool:latest"
                self.backend = "ollama"
                logger.info(f"Ollama client initialized: {base_url} with model {self.model_name}")
                return
            except Exception as e:
                logger.warning("Ollama client init failed, fallback enabled: %s", e)
                self.openai_client = None

        if backend == "gemini":
            try:
                api_key = os.getenv("GOOGLE_API_KEY")
                if not api_key:
                    raise ValueError("GOOGLE_API_KEY is missing")
                genai.configure(api_key=api_key)
                self.model_name = model or "gemini-3-pro-preview"
                self.gemini_model = genai.GenerativeModel(self.model_name)
                return
            except Exception as e:
                logger.warning("Gemini init failed, fallback enabled: %s", e)
                self.gemini_model = None

        self.openai_key = os.getenv("OPENAI_API_KEY")
        if self.openai_key:
            try:
                self.openai_client = OpenAI(api_key=self.openai_key)
                self.model_name = model or "gpt-5"
                self.backend = "openai"
            except Exception as e:
                logger.warning("OpenAI client init failed, fallback enabled: %s", e)
                self.openai_client = None

    def _rule_based_fallback(self, prompt: str, model_type: str = "performance") -> Dict[str, Any]:
        data_part = prompt
        if "\n" in prompt:
            data_part = prompt[prompt.rfind("\n", 0, prompt.find("\n\n") + 1):]
        text = data_part.lower()

        strong_keywords = [
            "dos attack", "ddos", "flood detected", "hulk", "goldeneye",
            "portscan", "port scan", "bruteforce", "brute force",
            "sql injection", "xss", "patator", "malicious",
            "intrusion detected", "suricata alert", "snort alert",
        ]
        hit_count = sum(1 for k in strong_keywords if k in text)
        verdict = "Malicious" if hit_count >= 3 else "Benign"
        summary = (
            f"Rule-based analysis complete. Verdict: {verdict}. "
            f"Detected {hit_count} strong suspicious signal(s) from the provided evidence."
        )
        return {
            "text": summary,
            "tokens": max(64, len(prompt.split()) // 2) if model_type == "performance" else 64,
            "success": True,
            "fallback": True,
        }

    async def call(self, prompt: str, model_type: str = "performance") -> Dict[str, Any]:
        try:
            if self.gemini_model:
                
                def _generate():
                    r = self.gemini_model.generate_content(prompt)
                    text = (r.text if hasattr(r, "text") else "") or ""
                    usage = getattr(r, "usage_metadata", None)
                    tokens = usage.total_token_count if usage and hasattr(usage, "total_token_count") else (len(prompt.split()) * 2)
                    return {"text": text, "tokens": tokens, "success": True}

                return await asyncio.to_thread(_generate)

            if self.openai_client:
                resp = self.openai_client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                )
                txt = resp.choices[0].message.content or ""
                tk = getattr(resp.usage, "total_tokens", len(prompt.split()) * 2)
                return {"text": txt, "tokens": tk, "success": True}

        except Exception as e:
            logger.warning("LLM call failed on backend=%s model=%s: %s", self.backend, self.model_name, e)

        return self._rule_based_fallback(prompt, model_type=model_type)

    async def call_performance_model(self, prompt: str, model_name: Optional[str] = None) -> Dict[str, Any]:
        return await self.call(prompt, model_type="performance")

class LocalSecurityAgent:
    def __init__(self, agent_id: str, domain: TaskType, data_path: str, llm: Optional[LLMProvider] = None):
        self.agent_id = agent_id
        self.domain = domain
        self.data_path = data_path
        self.llm = llm
        shared_bus.subscribe(domain, self.on_task_received)
        self.trajectory = []
        # 초기화 후 등록 메시지 발행 (이벤트 루프가 실행 중일 때 스케줄)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self._register())
        except RuntimeError:
            pass

    async def _register(self):
        reg = AgentRegistration(
            agent_id=self.agent_id,
            domain=self.domain.value,
            capabilities=[self.domain.value],
        )
        await shared_bus.publish(TaskType.AGENT_REGISTER, AgentMessage(
            header=MessageHeader(sender_id=self.agent_id),
            task_type=TaskType.AGENT_REGISTER,
            payload=reg.model_dump(),
        ))
        logger.info("Agent registered: %s (%s)", self.agent_id, self.domain.value)

    async def deregister(self):
        await shared_bus.publish(TaskType.AGENT_DEREGISTER, AgentMessage(
            header=MessageHeader(sender_id=self.agent_id),
            task_type=TaskType.AGENT_DEREGISTER,
            payload={"agent_id": self.agent_id, "domain": self.domain.value},
        ))
        logger.info("Agent deregistered: %s", self.agent_id)

    async def on_task_received(self, message: AgentMessage):
        try:
            await self._on_task_received_impl(message)
        except Exception as e:
            print(f"Exception in on_task_received: {e}", flush=True)
    async def _on_task_received_impl(self, message: AgentMessage):
        start_time = time.time()
        params = TaskParameter(**message.payload)

        print(f"Agent {self.agent_id} started on_task_received", flush=True)
        is_correct_tool = True

        if self.domain == TaskType.PACKET_ANALYSIS:
            tshark_filter = f"ip.addr == {params.target_ip}"
            is_valid_syntax = bool(re.match(r"ip\.(addr|src|dst) == \d+\.\d+\.\d+\.\d+", tshark_filter))
            raw_res = run_tshark(tshark_filter, self.data_path)
            tool_name = "tshark"
            tool_args = {"filter": tshark_filter}
        else:
            is_valid_syntax = True
            raw_res = grep_system_logs(params.target_ip, self.data_path)
            tool_name = "grep"
            tool_args = {"filter": params.target_ip}

        # 3-1. Hallucination Check (Entity Grounding)
        is_hallucinated = params.target_ip not in str(raw_res) if "Error" not in str(raw_res) else False

        verdict = "Benign"
        evidence_summary = str(raw_res)[:200]
        tokens_used = 0
        detected_patterns: List[str] = []

        has_raw_data = "Error" not in str(raw_res) and "No matching" not in str(raw_res) and str(raw_res).strip()

        if self.llm and has_raw_data:
            # raw data가 있을 때: 데이터 기반 분석
            prompt = (
                f"You are a network security analyst. Analyze the following raw security data for IP "
                f"{params.target_ip}.\n\nRespond with exactly one of:\n"
                f"VERDICT: Malicious\nVERDICT: Benign\n\nThen provide a brief explanation.\n\n"
                f"Raw data:\n{raw_res[:1000]}"
            )
        elif self.llm and params.question:
            # raw data 없지만 질문 컨텍스트가 있을 때: 질문 기반 분석
            prompt = (
                f"You are a network security analyst. There is no raw packet/log data available "
                f"for IP {params.target_ip}, but the following security question was raised:\n\n"
                f"\"{params.question}\"\n\n"
                f"Based solely on the threat description in this question, respond with exactly one of:\n"
                f"VERDICT: Malicious\nVERDICT: Benign\n\nThen provide a brief explanation."
            )
        else:
            prompt = None

        if self.llm and prompt:
            llm_res = await self.llm.call(prompt)
            txt = llm_res["text"]
            tokens_used = llm_res["tokens"]
            txt_l = txt.lower()
            # 명시적 VERDICT 태그 우선 파싱
            if "verdict: malicious" in txt_l:
                verdict = "Malicious"
            elif "verdict: benign" in txt_l:
                verdict = "Benign"
            else:
                # 부정 문맥 제거 후 판단 ("no attack", "not malicious" 등 제외)
                negation_phrases = [
                    "no attack", "not malicious", "no malicious", "no evidence of",
                    "no signs of", "appears benign", "normal traffic", "legitimate",
                ]
                has_negation = any(p in txt_l for p in negation_phrases)
                has_malicious = "malicious" in txt_l
                verdict = "Malicious" if has_malicious and not has_negation else "Benign"
            evidence_summary = txt
        else:
            # LLM 없을 때: raw data + question 키워드 기반 fallback
            combined_text = (str(raw_res) + " " + params.question).lower()
            strong_attack_signals = [
                "dos", "ddos", "flood", "hulk", "goldeneye", "portscan",
                "bruteforce", "patator", "sql injection", "intrusion",
                "rdp", "ransomware", "infiltration", "exploit", "malware",
                "brute force", "credential", "backdoor", "lateral movement",
            ]
            hit = sum(1 for k in strong_attack_signals if k in combined_text)
            if hit >= 2:
                verdict = "Malicious"

        if verdict == "Malicious":
            raw_lower = str(raw_res).lower()
            if "dos" in raw_lower or "flood" in raw_lower:
                detected_patterns.append("DoS")
            if "ftp" in raw_lower or "bruteforce" in raw_lower or "patator" in raw_lower:
                detected_patterns.append("BruteForce")
            if "portscan" in raw_lower or "scan" in raw_lower:
                detected_patterns.append("PortScan")
            if not detected_patterns:
                detected_patterns.append("anomaly")

        processing_latency = time.time() - start_time
        # Multi-Signal Confidence Calibration
        # ====================================
        # Each agent's confidence c_i is computed as a weighted sum of
        # four independently verifiable binary signals:
        #
        #   c_i = c_base + w1·S_tool + w2·S_ground + w3·S_pattern + w4·S_certain
        #
        # where:
        #   c_base    = 0.50  (baseline floor — prevents zero-confidence)
        #   S_tool    ∈ {0,1}: Did the analysis tool (tshark/grep) execute
        #                      successfully and return non-empty data?
        #   S_ground  ∈ {0,1}: Entity grounding — does the target IP appear
        #                      in the raw tool output? (anti-hallucination)
        #   S_pattern ∈ {0,1}: Were concrete attack patterns (DoS, BruteForce,
        #                      PortScan) detected in the evidence?
        #   S_certain ∈ {0,1}: Did the LLM produce an explicit VERDICT tag
        #                      without hedging language?
        #
        # Weights: w1=0.15, w2=0.15, w3=0.10, w4=0.09  (sum=0.49)
        # Range:   c_i ∈ [0.50, 0.99]
        #
        # Rationale: This formulation rewards agents whose conclusions are
        # grounded in real tool output and unambiguous reasoning, while
        # penalizing those relying on speculation or hallucinated context.
        # The bounded range [0.50, 0.99] prevents any single agent from
        # dominating the coordinator's majority-vote aggregation.

        s_tool = 1.0 if has_raw_data else 0.0
        s_ground = 0.0 if is_hallucinated else 1.0
        s_pattern = 1.0 if detected_patterns and detected_patterns != ["anomaly"] else 0.0

        # Linguistic certainty: explicit VERDICT tag without hedging
        hedging_words = ["might", "possibly", "could be", "unclear", "not sure",
                         "potentially", "seems", "appears to"]
        if tokens_used > 0:
            has_explicit_verdict = "verdict:" in evidence_summary.lower()
            has_hedging = any(w in evidence_summary.lower() for w in hedging_words)
            s_certain = 1.0 if (has_explicit_verdict and not has_hedging) else 0.0
        else:
            s_certain = 0.0

        confidence = min(0.50 + 0.15 * s_tool + 0.15 * s_ground + 0.10 * s_pattern + 0.09 * s_certain, 0.99)

        tool_info = ToolCallInfo(
            tool_name=tool_name,
            arguments=tool_args,
            is_valid_syntax=is_valid_syntax,
            is_correct_selection=is_correct_tool,
            execution_success="Error" not in str(raw_res),
            output_preview=str(raw_res)[:100]
        )

        intel = AgentIntelligence(
            task_id=params.task_id,
            agent_domain=self.domain.value,
            verdict=verdict,
            confidence=confidence,
            evidence_summary=evidence_summary,
            detected_patterns=detected_patterns,
            tool_calls=[tool_info],
            extracted_entities=[params.target_ip],
            processing_latency=processing_latency,
            tokens_consumed=tokens_used
        )

        payload = intel.model_dump() if hasattr(intel, "model_dump") else intel.dict()
        await shared_bus.publish(TaskType.MASTER_AGGREGATION, AgentMessage(
            header=MessageHeader(
                sender_id=self.agent_id,
                correlation_id=message.header.message_id,
            ),
            task_type=TaskType.MASTER_AGGREGATION,
            payload=payload
        ))

class MasterOrchestrator:
    # 보고서 수집 타임아웃 (초)
    REPORT_TIMEOUT = 300.0

    def __init__(self, agent_id: str, llm: LLMProvider):
        self.agent_id = agent_id
        self.llm = llm
        self.reports: List[AgentIntelligence] = []
        self.sub_goals: List[SubGoalStatus] = []
        self.turns = 0
        # agent_id → {domain, registered_at, status}
        self.agent_registry: Dict[str, Dict] = {}
        self._report_event = asyncio.Event()
        self._expected_reports = 0
        shared_bus.subscribe(TaskType.MASTER_AGGREGATION, self.on_report_received)
        shared_bus.subscribe(TaskType.AGENT_REGISTER, self.on_agent_registered)
        shared_bus.subscribe(TaskType.AGENT_DEREGISTER, self.on_agent_deregistered)

    async def on_agent_registered(self, message: AgentMessage):
        p = message.payload
        self.agent_registry[p["agent_id"]] = {
            "domain": p["domain"],
            "registered_at": p.get("registered_at", time.time()),
            "status": "online",
        }
        logger.info("Agent registered: %s (%s)", p["agent_id"], p["domain"])

    async def on_agent_deregistered(self, message: AgentMessage):
        agent_id = message.payload.get("agent_id", "")
        if agent_id in self.agent_registry:
            self.agent_registry[agent_id]["status"] = "offline"
        logger.info("Agent deregistered: %s", agent_id)

    async def on_report_received(self, message: AgentMessage):
        self.reports.append(AgentIntelligence(**message.payload))
        # 기대 보고서 수가 모이면 대기 이벤트 해제
        if self._expected_reports > 0 and len(self.reports) >= self._expected_reports:
            self._report_event.set()

    async def _wait_for_reports(self, expected: int, timeout: float = REPORT_TIMEOUT):
        """expected 개수의 보고서가 모일 때까지 대기. timeout 초과 시 부분 결과로 진행."""
        self._expected_reports = expected
        self._report_event.clear()
        if expected <= 0 or len(self.reports) >= expected:
            return
        try:
            await asyncio.wait_for(self._report_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(
                "Report collection timed out (%.1fs): received %d/%d",
                timeout, len(self.reports), expected,
            )
            # 타임아웃된 에이전트를 offline으로 표시
            responding_ids = {r.agent_domain for r in self.reports}
            for aid, info in self.agent_registry.items():
                if info["status"] == "online" and info["domain"] not in responding_ids:
                    info["status"] = "offline"
                    logger.warning("Agent marked offline (no response): %s", aid)

    def _extract_intent(self, query: str) -> Dict[str, Any]:
        """자연어 쿼리에서 target_ip와 분석 도메인을 추출한다."""
        ip_match = re.search(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b", query)
        target_ip = ip_match.group(1) if ip_match else None

        q = query.lower()
        domains: List[TaskType] = []
        if any(w in q for w in ["packet", "pcap", "traffic", "network", "flow", "port"]):
            domains.append(TaskType.PACKET_ANALYSIS)
        if any(w in q for w in ["log", "syslog", "event", "auth", "system", "journal"]):
            domains.append(TaskType.LOG_ANALYSIS)
        if not domains:
            domains = [TaskType.PACKET_ANALYSIS, TaskType.LOG_ANALYSIS]

        return {"target_ip": target_ip, "domains": domains}

    def _active_domains(self) -> List[TaskType]:
        """레지스트리에서 online 상태인 에이전트의 도메인 목록을 반환한다."""
        online = [
            TaskType(info["domain"])
            for info in self.agent_registry.values()
            if info["status"] == "online"
        ]
        return online if online else [TaskType.PACKET_ANALYSIS, TaskType.LOG_ANALYSIS]

    async def analyze_incident(self, target_ip: str):
        res = await self.run_scenario(f"Investigate suspicious activity from {target_ip}", target_ip)
        return res["verdict"]

    async def run_scenario(self, query: str, target_ip: Optional[str] = None):
        start_time = time.time()
        self.reports = []
        self.turns = 0

        # Sub-goal Completion Rate (SCR) Tracking
        self.sub_goals = [
            SubGoalStatus(description="Planning & Intent Extraction"),
            SubGoalStatus(description="Packet Evidence Collection"),
            SubGoalStatus(description="Log Correlation"),
            SubGoalStatus(description="Final Synthesis"),
        ]

        # Step 1: Intent analysis — 쿼리에서 IP 및 분석 범위 추출
        self.turns += 1
        intent = self._extract_intent(query)
        effective_ip = target_ip or intent["target_ip"] or "0.0.0.0"
        intent_domains = intent["domains"]
        plan_res = await self.llm.call(f"Plan analysis for: {query}")
        self.sub_goals[0].status = "success"

        # Step 2 & 3: 등록된 온라인 에이전트 중 intent 도메인과 교집합으로 디스패치
        self.turns += 1
        active = self._active_domains()
        dispatch_domains = [d for d in intent_domains if d in active] or active
        task_id = str(uuid.uuid4())
        task_payload = {"task_id": task_id, "target_ip": effective_ip, "time_window": "current", "question": query}

        publish_tasks = []
        for domain in dispatch_domains:
            msg = AgentMessage(
                header=MessageHeader(sender_id=self.agent_id),
                task_type=domain,
                payload=task_payload,
            )
            publish_tasks.append(shared_bus.publish(domain, msg))
        await asyncio.gather(*publish_tasks)

        # 보고서 수집 대기 (장애 감지 포함)
        await self._wait_for_reports(expected=len(dispatch_domains))

        self.sub_goals[1].status = "success" if any(
            r.agent_domain == TaskType.PACKET_ANALYSIS.value for r in self.reports
        ) else "failed"
        self.sub_goals[2].status = "success" if any(
            r.agent_domain == TaskType.LOG_ANALYSIS.value for r in self.reports
        ) else "failed"

        # Step 4: Synthesis — Confidence-Weighted Majority Vote
        # ======================================================
        # Given N agent reports, each with verdict v_i ∈ {Malicious, Benign}
        # and calibrated confidence c_i ∈ [0, 1], the aggregation proceeds:
        #
        #   S_mal = Σ c_i  for all i where v_i = "Malicious"
        #   S_ben = Σ c_i  for all i where v_i = "Benign"
        #   N_mal = |{i : v_i = "Malicious"}|
        #   N_ben = |{i : v_i = "Benign"}|
        #
        # Decision rule (majority-first with confidence tiebreak):
        #   if N_mal > N_ben:      final_verdict = "Malicious"
        #   elif N_ben > N_mal:    final_verdict = "Benign"
        #   else (tie):            final_verdict = "Malicious" if S_mal >= S_ben
        #                                         else "Benign"
        #
        # This two-stage approach ensures that:
        # 1. A clear majority always wins (democratic consensus).
        # 2. When agents are evenly split, the higher-confidence side prevails.
        # 3. No single high-confidence agent can override a consensus.
        self.turns += 1
        if self.reports:
            mal_score = sum(r.confidence for r in self.reports if r.verdict == "Malicious")
            ben_score = sum(r.confidence for r in self.reports if r.verdict == "Benign")
            mal_count = sum(1 for r in self.reports if r.verdict == "Malicious")
            ben_count = sum(1 for r in self.reports if r.verdict == "Benign")
            total = len(self.reports)
            # 다수결 우선: 과반이 Malicious면 Malicious
            # 동점이면 confidence-weighted로 결정 (편향 없음)
            if mal_count > ben_count:
                final_verdict = "Malicious"
            elif ben_count > mal_count:
                final_verdict = "Benign"
            else:
                final_verdict = "Malicious" if mal_score >= ben_score else "Benign"
        else:
            final_verdict = "Benign"
        self.sub_goals[3].status = "success"

        return {
            "verdict": final_verdict,
            "latency": time.time() - start_time,
            "turns": self.turns,
            "sub_goals": self.sub_goals,
            "reports": self.reports,
            "tokens": plan_res["tokens"] + 500,
        }


class ToolEnabledAgent:
    def __init__(self, pcap_path: str = "./data/CIC-IDS2017/Tuesday-WorkingHours.pcap", log_path: Optional[str] = None):
        self.pcap_path = pcap_path
        default_log = "./data/CIC-IDS2017/syslog_threats.log"
        self.log_path = log_path or (default_log if os.path.exists(default_log) else "./data/CIC-IDS2017/Tuesday-WorkingHours_converted.csv")

    def _extract_ip(self, text: str) -> str:
        m = re.search(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b", text)
        return m.group(1) if m else "192.168.10.50"

    async def ask(self, text: str) -> Dict[str, Any]:
        target_ip = self._extract_ip(text)
        shared_bus.reset()
        llm = LLMProvider(backend="auto")
        master = MasterOrchestrator("Master", llm)
        _ = LocalSecurityAgent("Packet", TaskType.PACKET_ANALYSIS, self.pcap_path, llm=llm)
        _ = LocalSecurityAgent("Log", TaskType.LOG_ANALYSIS, self.log_path, llm=llm)

        res = await master.run_scenario(text, target_ip)
        logs = [f"[{s.description}] {s.status}" for s in res["sub_goals"]]
        reports_data = []
        for i, r in enumerate(res.get("reports", [])):
            tc = getattr(r, "tool_calls", [])
            source = tc[0].tool_name if tc else f"agent_{i}"
            summary = (getattr(r, "evidence_summary", "") or "")
            logs.append(f"{getattr(r, 'verdict', 'N/A')}: {summary}")
            reports_data.append({"source": source, "verdict": getattr(r, "verdict", "N/A"), "evidence_summary": getattr(r, "evidence_summary", "")[:500]})

        summary_json = {
            "user_query": text,
            "target_ip": target_ip,
            "final_verdict": res["verdict"],
            "latency_sec": round(res["latency"], 2),
            "tokens_used": res.get("tokens", 0),
            "sub_goals": [{"description": s.description, "status": s.status} for s in res["sub_goals"]],
            "agent_reports": reports_data,
        }
        summary_str = json.dumps(summary_json, ensure_ascii=False, indent=2)

        prompt = f"""You are a security analyst assistant. A multi-agent system analyzed network traffic and logs. Below is the analysis result as JSON. The user asked: "{text}"

                    Analysis summary (JSON):
                    {summary_str}

                    Based on this analysis, provide a clear, professional answer in 2-4 sentences. Explain the verdict and key findings. Use Korean if the user wrote in Korean, otherwise English."""
        llm_res = await llm.call(prompt)
        answer = (llm_res.get("text") or "").strip() or f"**Verdict: {res['verdict']}** (분석 완료, {res['latency']:.2f}s 소요)"
        return {"execution_log": logs, "answer": answer}
