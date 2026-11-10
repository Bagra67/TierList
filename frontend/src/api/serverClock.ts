let serverClockOffsetMs: number = 0;

export function alignOnServerClock(serverNow: string): void {
  serverClockOffsetMs = Date.parse(serverNow) - Date.now();
}

export function serverTimeMs(): number {
  return Date.now() + serverClockOffsetMs;
}
