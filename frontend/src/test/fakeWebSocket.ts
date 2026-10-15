// Faux WebSocket : jsdom en ouvrirait un vrai vers le serveur de test. Il garde les messages
// envoyés par la page, et le test joue le serveur (ouverture, messages, fermeture).

interface FakeSocketEvent {
  data?: string;
  code?: number;
}

type FakeSocketListener = (event: FakeSocketEvent) => void;

export class FakeWebSocket {
  static readonly CONNECTING: number = 0;
  static readonly OPEN: number = 1;
  static readonly CLOSING: number = 2;
  static readonly CLOSED: number = 3;
  // Sockets ouverts depuis le début du test, du plus ancien au plus récent
  static instances: FakeWebSocket[] = [];

  readonly url: string;
  readyState: number = FakeWebSocket.CONNECTING;
  readonly sent: string[] = [];
  private readonly listeners: Map<string, FakeSocketListener[]> = new Map();

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }

  addEventListener(type: string, listener: FakeSocketListener): void {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), listener]);
  }

  send(data: string): void {
    this.sent.push(data);
  }

  close(code: number = 1000): void {
    if (this.readyState === FakeWebSocket.CLOSED) return;
    this.readyState = FakeWebSocket.CLOSED;
    this.dispatch('close', { code });
  }

  // --- Le serveur, joué par le test ------------------------------------------------------------

  acceptConnection(): void {
    this.readyState = FakeWebSocket.OPEN;
    this.dispatch('open', {});
  }

  receive(message: object): void {
    this.dispatch('message', { data: JSON.stringify(message) });
  }

  closeFromServer(code: number): void {
    this.readyState = FakeWebSocket.CLOSED;
    this.dispatch('close', { code });
  }

  sentMessages(): unknown[] {
    return this.sent.map((data: string) => JSON.parse(data) as unknown);
  }

  private dispatch(type: string, event: FakeSocketEvent): void {
    for (const listener of this.listeners.get(type) ?? []) listener(event);
  }
}

export function latestSocket(): FakeWebSocket {
  const socket: FakeWebSocket | undefined = FakeWebSocket.instances.at(-1);
  if (socket === undefined) throw new Error('No WebSocket opened');
  return socket;
}
