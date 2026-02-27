import os
import asyncio
import argparse
import logging

import pandas as pd

from src.agents import MasterOrchestrator, LocalSecurityAgent, LLMProvider
from src.bus import shared_bus
from src.protocol import TaskType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("multi-agent-pcaplog.main")


async def setup_data():
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "CIC-IDS2017")
    os.makedirs(data_dir, exist_ok=True)
    csv_path = os.path.join(data_dir, "Tuesday-WorkingHours.pcap_ISCX.csv")
    if not os.path.exists(csv_path):
        pd.DataFrame({
            "Source IP": ["192.168.10.50"],
            "Label": ["FTP-Patator"],
        }).to_csv(csv_path, index=False)
    pcap_path = os.path.join(data_dir, "Tuesday-WorkingHours.pcap")
    if not os.path.exists(pcap_path):
        with open(pcap_path, "w") as f:
            f.write("")


async def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Security Analysis System")
    parser.add_argument("--role", choices=["master", "packet", "log"], default="master",
                        help="Node role: master, packet, or log")
    args = parser.parse_args()

    role = os.getenv("AGENT_ROLE", args.role)
    
    logger.info(f"Starting node with role: {role}")

    await setup_data()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(root, "data", "CIC-IDS2017")
    pcap_path = os.path.join(data_path, "Tuesday-WorkingHours.pcap")
    csv_path = os.path.join(data_path, "Tuesday-WorkingHours.pcap_ISCX.csv")
    if not os.path.exists(csv_path):
        csv_path = os.path.join(root, "data", "Tuesday-WorkingHours_converted.csv")

    mas_backend = os.getenv("MAS_LLM_BACKEND", "ollama")
    mas_model = os.getenv("MAS_LLM_MODEL", "Llama-PcapLog-Tool")
    
    try:
        llm = LLMProvider(backend=mas_backend, model=mas_model)
        logger.info(f"LLM initialized: {mas_backend}/{mas_model}")
    except Exception as e:
        logger.error(f"LLM initialization failed: {e}")
        llm = LLMProvider(backend="auto")
    
    bus_task = asyncio.create_task(shared_bus.listen())

    try:
        if role == "master":
            logger.info("=== [Master Node] Starting ===")
            master = MasterOrchestrator("Master-Orchestrator", llm)
            
            logger.info("Waiting for worker nodes to be ready...")
            await asyncio.sleep(8)
            
            target_ip = os.getenv("TARGET_IP", "192.168.10.50")
            logger.info(f"Master: Starting analysis for {target_ip}")
            verdict = await master.analyze_incident(target_ip)
            logger.info(f"Final Verdict: {verdict}")
            
            await asyncio.sleep(5)
            logger.info("Master node shutting down")

        elif role == "packet":
            logger.info("=== [Packet Worker Node] Starting ===")
            packet_agent = LocalSecurityAgent(
                "Packet-Analytic-Agent", 
                TaskType.PACKET_ANALYSIS, 
                pcap_path, 
                llm=llm
            )
            logger.info(f"Packet agent ready, monitoring: {pcap_path}")
            await asyncio.Future()

        elif role == "log":
            logger.info("=== [Log Worker Node] Starting ===")
            log_agent = LocalSecurityAgent(
                "Log-Analytic-Agent", 
                TaskType.LOG_ANALYSIS, 
                csv_path, 
                llm=llm
            )
            logger.info(f"Log agent ready, monitoring: {csv_path}")
            await asyncio.Future()

    except asyncio.CancelledError:
        logger.info(f"{role} node received shutdown signal")
    except Exception as e:
        logger.error(f"Error in {role} node: {e}", exc_info=True)
    finally:
        bus_task.cancel()
        try:
            await bus_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
