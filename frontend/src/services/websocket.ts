import { io, Socket } from 'socket.io-client';

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'http://localhost:5001';

class WebSocketService {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;

  connect(token: string) {
    if (this.socket?.connected) {
      return;
    }

    this.socket = io(WS_BASE_URL, {
      auth: { token },
      transports: ['websocket'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: this.maxReconnectAttempts,
    });

    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    });

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      this.reconnectAttempts++;
    });

    this.socket.on('error', (error) => {
      console.error('WebSocket error:', error);
    });
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  // Market Data Subscriptions
  subscribeToChart(symbol: string, timeframe: string, callback: (data: any) => void) {
    if (!this.socket) return;

    this.socket.emit('subscribe_chart', { symbol, timeframe });
    this.socket.on('tick_update', callback);
    this.socket.on('candle_complete', callback);
    this.socket.on('indicator_update', callback);
  }

  unsubscribeFromChart(symbol: string, timeframe: string) {
    if (!this.socket) return;

    this.socket.emit('unsubscribe_chart', { symbol, timeframe });
    this.socket.off('tick_update');
    this.socket.off('candle_complete');
    this.socket.off('indicator_update');
  }

  // Trading Activity Updates
  onPositionUpdate(callback: (data: any) => void) {
    if (!this.socket) return;
    this.socket.on('position_update', callback);
  }

  onOrderUpdate(callback: (data: any) => void) {
    if (!this.socket) return;
    this.socket.on('order_update', callback);
  }

  onPnLUpdate(callback: (data: any) => void) {
    if (!this.socket) return;
    this.socket.on('pnl_update', callback);
  }

  onStrategyUpdate(callback: (data: any) => void) {
    if (!this.socket) return;
    this.socket.on('strategy_update', callback);
  }

  // Notifications
  onNotification(callback: (data: any) => void) {
    if (!this.socket) return;
    this.socket.on('notification', callback);
  }

  onNotificationRead(callback: (data: any) => void) {
    if (!this.socket) return;
    this.socket.on('notification_read', callback);
  }

  // Remove listeners
  removeListener(event: string, callback?: (data: any) => void) {
    if (!this.socket) return;
    if (callback) {
      this.socket.off(event, callback);
    } else {
      this.socket.off(event);
    }
  }

  // Check connection status
  isConnected(): boolean {
    return this.socket?.connected || false;
  }
}

export const wsService = new WebSocketService();
