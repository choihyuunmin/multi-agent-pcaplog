"""Structured Communication Protocol for Multi-Agent Security Analysis
================================================================

This module defines the structured data schemas used for inter-agent
communication in the Collaborative Multi-Agent Framework (CMAF).

All messages between the Master Coordinator and Network Analysis Agents
follow these Pydantic-based schemas, serialized as JSON over the message bus.

Key Design Decisions:
  - Pydantic BaseModel ensures type safety and serialization consistency.
  - Each AgentMessage wraps a typed payload with a standard MessageHeader.
  - AgentIntelligence carries the structured analysis result, including
    verdict, confidence score, evidence summary, and tool call metadata.

Example AgentIntelligence JSON (as transmitted over Redis Pub/Sub)::

    {
        "task_id": "a1b2c3d4-...",
        "agent_domain": "packet_analysis",
        "verdict": "Malicious",
        "confidence": 0.92,
        "evidence_summary": "Detected SYN flood pattern from 172.16.0.1...",
        "detected_patterns": ["DoS", "SYN Flood"],
        "tool_calls": [
            {
                "tool_name": "tshark",
                "arguments": {"filter": "ip.addr == 172.16.0.1"},
                "is_valid_syntax": true,
                "is_correct_selection": true,
                "execution_success": true,
                "output_preview": "0.000000 172.16.0.1 -> 192.168.10.50 ..."
            }
        ],
        "extracted_entities": ["172.16.0.1"],
        "processing_latency": 1.23,
        "tokens_consumed": 256
    }

Protocol Version: 1.0
"""

import uuid
import time

from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

PROTOCOL_VERSION = "1.0"

class TaskType(str, Enum):
    """Message routing topics for the Pub/Sub message bus.

    Attributes:
        PACKET_ANALYSIS: Task dispatched to Packet Analysis Agent (tshark-based).
        LOG_ANALYSIS: Task dispatched to Log Analysis Agent (grep/syslog-based).
        MASTER_PLANNING: Internal planning phase within the Master Coordinator.
        MASTER_AGGREGATION: Agent intelligence reports sent back to the Coordinator.
        AGENT_REGISTER: Agent lifecycle — registration announcement.
        AGENT_DEREGISTER: Agent lifecycle — deregistration announcement.
    """
    PACKET_ANALYSIS = "packet_analysis"
    LOG_ANALYSIS = "log_analysis"
    MASTER_PLANNING = "master_planning"
    MASTER_AGGREGATION = "master_aggregation"
    AGENT_REGISTER = "agent_register"
    AGENT_DEREGISTER = "agent_deregister"

class ToolCallInfo(BaseModel):
    """Metadata for a single tool invocation by an agent.

    Fields:
        tool_name: Name of the invoked tool ("tshark" or "grep").
        arguments: Tool arguments as key-value pairs (e.g., {"filter": "ip.addr == ..."}).
        is_valid_syntax: Whether the tool arguments passed syntax validation.
        is_correct_selection: Whether the tool was appropriate for the task domain.
        execution_success: Whether the tool executed without errors.
        output_preview: First 100 chars of tool output for debugging/logging.
    """
    tool_name: str
    arguments: Dict[str, Any]
    is_valid_syntax: bool = True
    is_correct_selection: bool = True
    execution_success: bool = True
    output_preview: str = ""

class SubGoalStatus(BaseModel):
    description: str
    status: str = "pending"
    latency: float = 0.0

class TaskParameter(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    target_ip: str
    time_window: str = "current"
    features_to_extract: List[str] = []
    question: str = ""  # 원본 분석 질문 (raw data 없을 때 LLM 컨텍스트로 활용)

class MessageHeader(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str
    timestamp: float = Field(default_factory=time.time)
    protocol_version: str = Field(default=PROTOCOL_VERSION)
    correlation_id: Optional[str] = None

class AgentIntelligence(BaseModel):
    """Structured analysis report returned by each Network Analysis Agent.

    This is the core data schema transmitted from agents to the Master
    Coordinator via the MASTER_AGGREGATION topic. The Coordinator uses
    these reports for confidence-weighted aggregation.

    Fields:
        task_id: Unique identifier linking this report to the dispatched task.
        agent_domain: Domain of the reporting agent ("packet_analysis" or "log_analysis").
        verdict: Binary classification result — "Malicious" or "Benign".
        confidence: Confidence score in [0.0, 1.0], used for weighted voting.
                    Calculated via multi-signal calibration:
                    c_i = 0.50 + 0.15*S_tool + 0.15*S_ground + 0.10*S_pattern + 0.09*S_certain
        evidence_summary: Natural language summary of the analysis findings.
        detected_patterns: List of detected attack pattern names (e.g., ["DoS", "BruteForce"]).
        tool_calls: Metadata for each tool invocation during analysis.
        sub_goals: Status of sub-tasks within the analysis pipeline.
        tokens_consumed: Total LLM tokens used for this analysis.
        processing_latency: Wall-clock time (seconds) for the agent's analysis.
        extracted_entities: IP addresses and other entities found in the data.
    """
    task_id: str = ""
    agent_domain: str = ""
    verdict: str
    confidence: float
    evidence_summary: str
    detected_patterns: List[str]
    tool_calls: List[ToolCallInfo] = []
    sub_goals: List[SubGoalStatus] = []
    tokens_consumed: int = 0
    processing_latency: float = 0.0
    extracted_entities: List[str] = []

class AgentRegistration(BaseModel):
    agent_id: str
    domain: str
    capabilities: List[str] = []
    registered_at: float = Field(default_factory=time.time)

class AgentMessage(BaseModel):
    header: MessageHeader
    task_type: TaskType
    payload: Dict[str, Any]