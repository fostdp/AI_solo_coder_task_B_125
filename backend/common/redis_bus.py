import asyncio
import json
from typing import Dict, Any, Callable, Optional
from contextlib import asynccontextmanager
import logging

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisMessageBus:
    """Redis Pub/Sub 消息总线 - 用于服务间通信"""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self._client: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.PubSub] = None
        self._subscribers: Dict[str, Callable] = {}
        self._listen_task: Optional[asyncio.Task] = None
        self._is_connected = False

    async def connect(self) -> None:
        """连接Redis"""
        if self._is_connected:
            return
        try:
            self._client = redis.from_url(self.redis_url, decode_responses=True)
            await self._client.ping()
            self._pubsub = self._client.pubsub()
            self._is_connected = True
            logger.info("Redis消息总线连接成功")
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            raise

    async def disconnect(self) -> None:
        """断开连接"""
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        if self._pubsub:
            await self._pubsub.close()
        if self._client:
            await self._client.close()
        self._is_connected = False
        logger.info("Redis消息总线已断开")

    async def publish(self, channel: str, message: Dict[str, Any]) -> None:
        """发布消息到指定频道"""
        if not self._client:
            raise RuntimeError("Redis未连接")
        message_str = json.dumps(message, ensure_ascii=False, default=str)
        await self._client.publish(channel, message_str)
        logger.debug(f"发布消息到频道 {channel}: {message.get('type', 'unknown')}")

    async def subscribe(self, channel: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """订阅频道并注册消息处理器"""
        if not self._pubsub:
            raise RuntimeError("Redis PubSub未初始化")
        self._subscribers[channel] = handler
        await self._pubsub.subscribe(channel)
        logger.info(f"订阅频道: {channel}")

        if not self._listen_task:
            self._listen_task = asyncio.create_task(self._listen_loop())

    async def unsubscribe(self, channel: str) -> None:
        """取消订阅频道"""
        if self._pubsub and channel in self._subscribers:
            await self._pubsub.unsubscribe(channel)
            del self._subscribers[channel]
            logger.info(f"取消订阅频道: {channel}")

    async def _listen_loop(self) -> None:
        """监听消息循环"""
        if not self._pubsub:
            return
        try:
            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"]
                    try:
                        data = json.loads(message["data"])
                        handler = self._subscribers.get(channel)
                        if handler:
                            if asyncio.iscoroutinefunction(handler):
                                await handler(data)
                            else:
                                handler(data)
                    except json.JSONDecodeError as e:
                        logger.error(f"消息解析失败 {channel}: {e}")
                    except Exception as e:
                        logger.error(f"消息处理异常 {channel}: {e}", exc_info=True)
        except asyncio.CancelledError:
            logger.info("消息监听已取消")
        except Exception as e:
            logger.error(f"消息监听异常: {e}", exc_info=True)

    async def set_key(self, key: str, value: str, expire: Optional[int] = None) -> None:
        """设置缓存键值"""
        if not self._client:
            raise RuntimeError("Redis未连接")
        if expire:
            await self._client.setex(key, expire, value)
        else:
            await self._client.set(key, value)

    async def get_key(self, key: str) -> Optional[str]:
        """获取缓存值"""
        if not self._client:
            raise RuntimeError("Redis未连接")
        return await self._client.get(key)


_instance: Optional[RedisMessageBus] = None


def get_redis_bus(redis_url: Optional[str] = None) -> RedisMessageBus:
    """获取Redis消息总线单例"""
    global _instance
    if _instance is None:
        if redis_url is None:
            redis_url = "redis://localhost:6379/0"
        _instance = RedisMessageBus(redis_url)
    return _instance
