import uuid
import time

from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

PROTOCOL_VERSION = "1.0"

class TaskType(str, Enum):
    PACKET_ANALYSIS = "packet_analysis"
    LOG_ANALYSIS = "log_analysis"
    MASTER_PLANNING = "master_planning"
    MASTER_AGGREGATION = "master_aggregation"
    AGENT_REGISTER = "agent_register"
    AGENT_DEREGISTER = "agent_deregister"

class ToolCallInfo(BaseModel):
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