// Type aligné sur HelloResponse (backend/app/main.py)
export interface HelloResponse {
  message: string;
}

// '/api' est redirigé vers le backend FastAPI par le proxy Vite (vite.config.ts)
export async function getHello(signal?: AbortSignal): Promise<HelloResponse> {
  const response = await fetch('/api/hello', { signal });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json() as Promise<HelloResponse>;
}
