import { spawnSync } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { E2E_APP_URL, E2E_DATABASE } from './app.ts';

const FRONTEND_DIR: string = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
export const BACKEND_DIR: string = resolve(FRONTEND_DIR, '..', 'backend');
export const FRONTEND_BUILD_DIR: string = resolve(FRONTEND_DIR, 'dist');

export const appEnvironment: NodeJS.ProcessEnv = {
  ...process.env,
  VIRTUAL_ENV: undefined,
  PYTHONUTF8: '1',
  POSTGRES_DB: E2E_DATABASE,
  FRONTEND_DIST: FRONTEND_BUILD_DIR,
  FRONTEND_BASE_URL: E2E_APP_URL,
  AUTH_COOKIE_SECURE: 'false',
  SMTP_HOST: '127.0.0.1',
  SMTP_PORT: '1025',
  SMTP_STARTTLS: 'false',
  MAINTENANCE_ENABLED: 'false',
};

export function runInBackend(args: string[]): void {
  const result = spawnSync('uv', ['run', ...args], {
    cwd: BACKEND_DIR,
    env: appEnvironment,
    stdio: 'inherit',
  });
  if (result.status !== 0) {
    throw new Error(`e2e: "uv run ${args.join(' ')}" failed`);
  }
}
