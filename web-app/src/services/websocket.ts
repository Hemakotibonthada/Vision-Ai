/**
 * WebSocket service for real-time communication
 */
type MessageHandler = (data: any) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private handlers: Map<string, Set<MessageHandler>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectDelay = 1000;
  private channel: string;
  private url: string;

  constructor() {
    this.channel = 'default';
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    this.url = `${protocol}//${window.location.host}/ws`;
  }

  connect(channel: string = 'default'): void {
    this.channel = channel;
    if (this.ws?.readyState === WebSocket.OPEN) return;

    try {
      this.ws = new WebSocket(`${this.url}/${channel}`);

      this.ws.onopen = () => {
        console.log(`WebSocket connected to channel: ${channel}`);
        this.reconnectAttempts = 0;
        this.emit('connection', { status: 'connected', channel });
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.emit(data.type || 'message', data);
          this.emit('*', data);
        } catch {
          this.emit('raw', event.data);
        }
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.emit('connection', { status: 'disconnected' });
        this.attemptReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.emit('error', { error });
      };
    } catch (e) {
      console.error('WebSocket connection failed:', e);
    }
  }

  disconnect(): void {
    this.reconnectAttempts = this.maxReconnectAttempts; // prevent reconnect
    this.ws?.close();
    this.ws = null;
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return;
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    setTimeout(() => this.connect(this.channel), delay);
  }

  send(data: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(typeof data === 'string' ? data : JSON.stringify(data));
    }
  }

  sendDetection(imageBase64: string): void {
    this.send({ type: 'detect', image: imageBase64 });
  }

  publishMqtt(topic: string, payload: any): void {
    this.send({ type: 'mqtt_publish', topic, payload });
  }

  ping(): void {
    this.send({ type: 'ping' });
  }

  on(event: string, handler: MessageHandler): () => void {
    if (!this.handlers.has(event)) this.handlers.set(event, new Set());
    this.handlers.get(event)!.add(handler);
    return () => this.off(event, handler);
  }

  off(event: string, handler: MessageHandler): void {
    this.handlers.get(event)?.delete(handler);
  }

  private emit(event: string, data: any): void {
    this.handlers.get(event)?.forEach((h) => h(data));
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

export const wsService = new WebSocketService();
export default wsService;
