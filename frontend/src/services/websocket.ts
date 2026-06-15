import ReconnectingWebSocket from 'reconnecting-websocket'
import { useStore } from '@/store/useStore'
import type { WebSocketMessage } from '@/types'

class WebSocketService {
  private sockets: Map<string, ReconnectingWebSocket> = new Map()
  private messageHandlers: Map<string, Set<(message: WebSocketMessage) => void>> = new Map()

  connect(room: string, onMessage?: (message: WebSocketMessage) => void): ReconnectingWebSocket {
    if (this.sockets.has(room)) {
      return this.sockets.get(room)!
    }

    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'
    const url = `${wsUrl}/ws/${room}`

    const socket = new ReconnectingWebSocket(url, [], {
      maxReconnectionDelay: 10000,
      minReconnectionDelay: 1000,
      reconnectionDelayGrowFactor: 1.3
    })

    socket.addEventListener('open', () => {
      console.log(`WebSocket [${room}] 已连接`)
      useStore.getState().setWsConnectionStatus('connected')
    })

    socket.addEventListener('close', () => {
      console.log(`WebSocket [${room}] 已断开`)
      useStore.getState().setWsConnectionStatus('disconnected')
    })

    socket.addEventListener('error', (error) => {
      console.error(`WebSocket [${room}] 错误:`, error)
    })

    socket.addEventListener('message', (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data)
        
        useStore.getState().handleWebSocketMessage(message)
        
        const handlers = this.messageHandlers.get(room)
        if (handlers) {
          handlers.forEach(handler => handler(message))
        }
      } catch (e) {
        console.error('WebSocket消息解析错误:', e)
      }
    })

    this.sockets.set(room, socket)

    if (onMessage) {
      this.addMessageHandler(room, onMessage)
    }

    return socket
  }

  addMessageHandler(room: string, handler: (message: WebSocketMessage) => void) {
    if (!this.messageHandlers.has(room)) {
      this.messageHandlers.set(room, new Set())
    }
    this.messageHandlers.get(room)!.add(handler)
  }

  removeMessageHandler(room: string, handler: (message: WebSocketMessage) => void) {
    const handlers = this.messageHandlers.get(room)
    if (handlers) {
      handlers.delete(handler)
    }
  }

  send(room: string, data: any) {
    const socket = this.sockets.get(room)
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(data))
    }
  }

  disconnect(room: string) {
    const socket = this.sockets.get(room)
    if (socket) {
      socket.close()
      this.sockets.delete(room)
      this.messageHandlers.delete(room)
    }
  }

  disconnectAll() {
    this.sockets.forEach((socket) => socket.close())
    this.sockets.clear()
    this.messageHandlers.clear()
  }

  isConnected(room: string): boolean {
    const socket = this.sockets.get(room)
    return socket?.readyState === WebSocket.OPEN ?? false
  }
}

export const wsService = new WebSocketService()

export const useWebSocket = (room: string, onMessage?: (message: WebSocketMessage) => void) => {
  return {
    connect: () => wsService.connect(room, onMessage),
    disconnect: () => wsService.disconnect(room),
    send: (data: any) => wsService.send(room, data),
    isConnected: () => wsService.isConnected(room)
  }
}
