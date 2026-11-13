let serverClockOffsetMs: number = 0;

export function alignOnServerClock(serverNow: string): void {
  serverClockOffsetMs = Date.parse(serverNow) - Date.now();
}

export function resetServerClock(): void {
  serverClockOffsetMs = 0;
}

export function serverTimeMs(): number {
  return Date.now() + serverClockOffsetMs;
}
