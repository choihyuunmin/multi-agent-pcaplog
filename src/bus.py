import os
import json
import asyncio
import logging

from typing import Dict, List, Callable, Awaitable, Optional, Any, Union

from src.protocol import AgentMessage, TaskType

logger = logging.getLogger(__name__)

PUBSUB_LOG_PATH = os.environ.get("PUBSUB_LOG_PATH", "results/pubsub_messages.jsonl")

def _message_to_json_dict(msg: AgentMessage) -> dict:
    header = msg.header.model_dump() if hasattr(msg.header, "model_dump") else msg.header.dict()
    return {
        "task_type": msg.task_type.value,
        "header": header,
        "payload": msg.payload,
    }


def _append_pubsub_log(topic: TaskType, message: AgentMessage):
    try:
        os.makedirs(os.path.dirname(PUBSUB_LOG_PATH) or ".", exist_ok=True)
        record = _message_to_json_dict(message)
        with open(PUBSUB_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        pass


class LocalMessageBus:
    def __init__(self):
        self._callbacks: Dict[str, List[Callable[[AgentMessage], Awaitable[None]]]] = {}

    def subscribe(self, topic: TaskType, callback: Callable[[AgentMessage], Awaitable[None]]):
        topic_name = str(topic.value)
        if topic_name not in self._callbacks:
            self._callbacks[topic_name] = []
        self._callbacks[topic_name].append(callback)

    async def publish(self, topic: TaskType, message: AgentMessage):
        topic_name = str(topic.value)
        _append_pubsub_log(topic, message)
        if topic_name in self._callbacks:
            tasks = [cb(message) for cb in self._callbacks[topic_name]]
            await asyncio.gather(*tasks)

    async def listen(self):
        await asyncio.Future()

    def reset(self):
        self._callbacks.clear()

    @staticmethod
    def clear_pubsub_log():
        try:
            if os.path.exists(PUBSUB_LOG_PATH):
                os.remove(PUBSUB_LOG_PATH)
        except Exception:
            pass


class RedisMessageBus:
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_client: Optional[Any] = None
        self.pubsub: Optional[Any] = None
        self._callbacks: Dict[str, List[Callable[[AgentMessage], Awaitable[None]]]] = {}
        self._listen_task: Optional[asyncio.Task] = None
        self._initialized = False

    async def _ensure_connected(self):
        if self._initialized:
            return
        
        try:
            import redis.asyncio as aioredis
            self.redis_client = await aioredis.from_url(
                f"redis://{self.redis_host}:{self.redis_port}",
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            self.pubsub = self.redis_client.pubsub()
            self._initialized = True
            logger.info(f"Redis connected: {self.redis_host}:{self.redis_port}")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise

    def subscribe(self, topic: TaskType, callback: Callable[[AgentMessage], Awaitable[None]]):
        topic_name = str(topic.value)
        if topic_name not in self._callbacks:
            self._callbacks[topic_name] = []
        self._callbacks[topic_name].append(callback)

    async def publish(self, topic: TaskType, message: AgentMessage):
        await self._ensure_connected()
        topic_name = str(topic.value)
        _append_pubsub_log(topic, message)
        
        msg_dict = {
            "header": message.header.model_dump() if hasattr(message.header, "model_dump") else message.header.dict(),
            "task_type": message.task_type.value,
            "payload": message.payload
        }
        msg_json = json.dumps(msg_dict, ensure_ascii=False)
        
        try:
            await self.redis_client.publish(topic_name, msg_json)
            logger.debug(f"Published to {topic_name}: {message.header.message_id[:8]}")
        except Exception as e:
            logger.error(f"Publish failed: {e}")

    async def listen(self):
        await self._ensure_connected()
        
        for topic_name in self._callbacks.keys():
            await self.pubsub.subscribe(topic_name)
            logger.info(f"Subscribed to Redis channel: {topic_name}")

        logger.info("Redis listener started")
        
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"]
                    data = message["data"]
                    
                    try:
                        msg_dict = json.loads(data)
                        from src.protocol import MessageHeader
                        agent_msg = AgentMessage(
                            header=MessageHeader(**msg_dict["header"]),
                            task_type=TaskType(msg_dict["task_type"]),
                            payload=msg_dict["payload"]
                        )
                        
                        if channel in self._callbacks:
                            tasks = [cb(agent_msg) for cb in self._callbacks[channel]]
                            await asyncio.gather(*tasks, return_exceptions=True)
                    except Exception as e:
                        logger.error(f"Message processing error: {e}")
        except asyncio.CancelledError:
            logger.info("Redis listener stopped")
            raise
        except Exception as e:
            logger.error(f"Redis listen error: {e}")

    def reset(self):
        self._callbacks.clear()

    @staticmethod
    def clear_pubsub_log():
        try:
            if os.path.exists(PUBSUB_LOG_PATH):
                os.remove(PUBSUB_LOG_PATH)
        except Exception:
            pass


def create_message_bus() -> Union[LocalMessageBus, RedisMessageBus]:
    redis_host = os.getenv("REDIS_HOST")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    
    if redis_host:
        logger.info(f"Using Redis message bus: {redis_host}:{redis_port}")
        return RedisMessageBus(redis_host, redis_port)
    else:
        logger.info("Using local message bus (in-memory)")
        return LocalMessageBus()


shared_bus = create_message_bus()
