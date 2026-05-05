# CMAF System Control Flow

This document illustrates the detailed control flow of the Collaborative Multi-Agent Framework (CMAF) during a security analysis task, directly addressing reproducibility and architectural specifics.

## Detailed Control Flow Diagram

```mermaid
sequenceDiagram
    participant User
    participant Master as Master Coordinator
    participant Redis as Redis Pub/Sub
    participant P_Agent as Packet Analysis Agent
    participant L_Agent as Log Analysis Agent
    
    User->>Master: Send Query / Alert triggered
    activate Master
    
    %% Planning Phase
    Master->>Master: Extract Intent & Entities (IP, Time)
    Master->>Master: Formulate Sub-goals (Planning)
    
    %% Task Delegation
    Master->>Redis: Publish [TaskType.PACKET_ANALYSIS]<br/>{"task_id": "...", "target_ip": "..."}
    Master->>Redis: Publish [TaskType.LOG_ANALYSIS]<br/>{"task_id": "...", "target_ip": "..."}
    
    %% Parallel Agent Processing
    par Network Packet Analysis
        Redis-->>P_Agent: Subscribe & Receive Task
        activate P_Agent
        P_Agent->>P_Agent: Form TShark Filter ("ip.addr == ...")
        P_Agent->>System (PCAP): Run TShark Extract
        System (PCAP)-->>P_Agent: Raw Packets (Text)
        P_Agent->>LLM (Llama-PcapLog): Prompt: "Analyze raw packets for Malicious/Benign"
        LLM (Llama-PcapLog)-->>P_Agent: Structured Analysis (Verdict, Reason)
        P_Agent->>P_Agent: Calculate Tool Usage & Confidence
        P_Agent->>Redis: Publish [TaskType.MASTER_AGGREGATION]
        deactivate P_Agent
    and System Log Analysis
        Redis-->>L_Agent: Subscribe & Receive Task
        activate L_Agent
        L_Agent->>L_Agent: Form Grep/Search Rule
        L_Agent->>System (Syslog): Search Target IP
        System (Syslog)-->>L_Agent: Matched Logs (Text)
        L_Agent->>LLM (Llama-PcapLog): Prompt: "Analyze syslog for Malicious/Benign"
        LLM (Llama-PcapLog)-->>L_Agent: Structured Analysis (Verdict, Reason)
        L_Agent->>L_Agent: Calculate Tool Usage & Confidence
        L_Agent->>Redis: Publish [TaskType.MASTER_AGGREGATION]
        deactivate L_Agent
    end
    
    %% Aggregation Phase
    Redis-->>Master: Receive Report (Packet)
    Redis-->>Master: Receive Report (Log)
    
    Master->>Master: Await Reports (Timeout: 30s)
    Master->>Master: Apply Confidence-Weighted<br/>Majority Vote
    
    %% Final Output
    Master->>Master: Generate Final Synthesis
    Master-->>User: Output Verdict & Explanation
    deactivate Master
```

### Key Mechanisms:
1. **Asynchronous Parallelism**: The `Master Coordinator` distributes tasks to specialized agents concurrently via `Redis Pub/Sub`.
2. **Contextual Tool Execution**: Each agent executes domain-specific tools (`tshark` for packets, `grep` for system logs) autonomously based on the Master's target IP.
3. **Local LLM Inference**: Information extraction and semantic analysis are processed locally at the edge using the fine-tuned `Llama-PcapLog` model, minimizing raw data transmission to the Master.
4. **Resilient Aggregation**: The Master collects structured `AgentIntelligence` reports and derives the final verdict using a Confidence-Weighted Majority Vote, neutralizing erroneous or low-confidence edge agents (benign hallucinations).
