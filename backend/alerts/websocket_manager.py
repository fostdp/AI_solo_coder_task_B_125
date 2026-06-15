import asyncio
import json
import uuid
from typing import Dict, List, Set, Optional, Any
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect

from core.models import Alert


class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_rooms: Dict[str, Set[str]] = {
            'monitoring': set(),
            'alerts': set(),
            'simulation': set(),
            'damage': set()
        }
        self.client_rooms: Dict[str, List[str]] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self._is_running = False

    async def start(self):
        """启动消息广播任务"""
        if not self._is_running:
            self._is_running = True
            asyncio.create_task(self._broadcast_task())

    async def stop(self):
        """停止消息广播"""
        self._is_running = False

    async def connect(self, websocket: WebSocket, client_id: Optional[str] = None) -> str:
        """
        客户端连接

        Args:
            websocket: WebSocket连接
            client_id: 客户端ID（可选）

        Returns:
            client_id: 分配的客户端ID
        """
        if client_id is None:
            client_id = str(uuid.uuid4())

        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.client_rooms[client_id] = []

        await self._send_message(client_id, {
            'type': 'connection_established',
            'client_id': client_id,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

        return client_id

    async def disconnect(self, client_id: str):
        """
        客户端断开连接

        Args:
            client_id: 客户端ID
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]

        if client_id in self.client_rooms:
            for room in self.client_rooms[client_id]:
                if client_id in self.connection_rooms.get(room, set()):
                    self.connection_rooms[room].discard(client_id)
            del self.client_rooms[client_id]

    async def subscribe(self, client_id: str, room: str):
        """
        订阅房间

        Args:
            client_id: 客户端ID
            room: 房间名称
        """
        if room not in self.connection_rooms:
            self.connection_rooms[room] = set()

        self.connection_rooms[room].add(client_id)

        if client_id not in self.client_rooms:
            self.client_rooms[client_id] = []

        if room not in self.client_rooms[client_id]:
            self.client_rooms[client_id].append(room)

        await self._send_message(client_id, {
            'type': 'subscribed',
            'room': room,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

    async def unsubscribe(self, client_id: str, room: str):
        """
        取消订阅房间

        Args:
            client_id: 客户端ID
            room: 房间名称
        """
        if room in self.connection_rooms:
            self.connection_rooms[room].discard(client_id)

        if client_id in self.client_rooms and room in self.client_rooms[client_id]:
            self.client_rooms[client_id].remove(room)

        await self._send_message(client_id, {
            'type': 'unsubscribed',
            'room': room,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

    async def broadcast_to_room(self, room: str, message: Dict[str, Any]):
        """
        向房间广播消息

        Args:
            room: 房间名称
            message: 消息内容
        """
        message['timestamp'] = datetime.now(timezone.utc).isoformat()
        message['room'] = room

        await self.message_queue.put((room, message))

    async def broadcast_sensor_data(self, sensor_data: Dict[str, Any]):
        """广播传感器数据"""
        message = {
            'type': 'sensor_data',
            'payload': sensor_data
        }
        await self.broadcast_to_room('monitoring', message)

    async def broadcast_alert(self, alert: Alert):
        """广播告警消息"""
        message = {
            'type': 'alert',
            'payload': {
                'id': str(alert.id),
                'alert_type': alert.alert_type,
                'floor_number': alert.floor_number,
                'threshold_value': alert.threshold_value,
                'actual_value': alert.actual_value,
                'severity': alert.severity,
                'status': alert.status,
                'created_at': alert.created_at.isoformat() if alert.created_at else None,
                'note': alert.note
            }
        }
        await self.broadcast_to_room('alerts', message)
        await self.broadcast_to_room('monitoring', message)

    async def broadcast_simulation_progress(self, simulation_id: str, status: str,
                                             progress: float = 0.0, message: str = ''):
        """广播仿真进度"""
        msg = {
            'type': 'simulation_progress',
            'payload': {
                'simulation_id': simulation_id,
                'status': status,
                'progress': progress,
                'message': message
            }
        }
        await self.broadcast_to_room('simulation', msg)

    async def broadcast_damage_result(self, damage_result: Dict[str, Any]):
        """广播损伤识别结果"""
        message = {
            'type': 'damage_result',
            'payload': damage_result
        }
        await self.broadcast_to_room('damage', message)
        await self.broadcast_to_room('monitoring', message)

    async def _broadcast_task(self):
        """后台广播任务"""
        while self._is_running:
            try:
                room, message = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=1.0
                )

                clients = self.connection_rooms.get(room, set()).copy()

                for client_id in list(clients):
                    if client_id in self.active_connections:
                        try:
                            await self._send_message(client_id, message)
                        except Exception:
                            await self.disconnect(client_id)

                self.message_queue.task_done()

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"广播任务异常: {e}")
                await asyncio.sleep(1.0)

    async def _send_message(self, client_id: str, message: Dict[str, Any]):
        """
        向单个客户端发送消息

        Args:
            client_id: 客户端ID
            message: 消息内容
        """
        websocket = self.active_connections.get(client_id)
        if websocket:
            try:
                await websocket.send_text(json.dumps(message, default=str))
            except Exception as e:
                print(f"发送消息失败 {client_id}: {e}")
                await self.disconnect(client_id)

    async def handle_client_message(self, client_id: str, message: str):
        """
        处理客户端消息

        Args:
            client_id: 客户端ID
            message: 消息内容
        """
        try:
            data = json.loads(message)
            action = data.get('action')

            if action == 'subscribe':
                room = data.get('room')
                if room:
                    await self.subscribe(client_id, room)

            elif action == 'unsubscribe':
                room = data.get('room')
                if room:
                    await self.unsubscribe(client_id, room)

            elif action == 'ping':
                await self._send_message(client_id, {
                    'type': 'pong',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })

            elif action == 'get_rooms':
                await self._send_message(client_id, {
                    'type': 'rooms_list',
                    'rooms': list(self.connection_rooms.keys()),
                    'subscribed': self.client_rooms.get(client_id, [])
                })

        except json.JSONDecodeError:
            await self._send_message(client_id, {
                'type': 'error',
                'message': '无效的JSON格式'
            })

    def get_connection_count(self) -> int:
        """获取当前连接数"""
        return len(self.active_connections)

    def get_room_members(self, room: str) -> List[str]:
        """获取房间成员列表"""
        return list(self.connection_rooms.get(room, set()))


manager = ConnectionManager()
