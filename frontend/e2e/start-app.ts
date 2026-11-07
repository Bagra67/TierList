import { spawn, spawnSync, type ChildProcess } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { E2E_APP_PORT, E2E_APP_URL, E2E_DATABASE } from './support/app.ts';

const FRONTEND_DIR: string = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const BACKEND_DIR: string = resolve(FRONTEND_DIR, '..', 'backend');
const FRONTEND_BUILD_DIR: string = resolve(FRONTEND_DIR, 'dist');

const CREATE_DATABASE_IF_MISSING: string = `
from sqlalchemy import create_engine, text
from app.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
with engine.connect() as connection:
    exists = connection.execute(
        text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": settings.postgres_db}
    ).scalar()
    if exists is None:
        quoted = connection.dialect.identifier_preparer.quote(settings.postgres_db)
        connection.execute(text(f"CREATE DATABASE {quoted}"))
`;

const appEnvironment: NodeJS.ProcessEnv = {
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

function runInBackend(args: string[]): void {
  const result = spawnSync('uv', ['run', ...args], {
    cwd: BACKEND_DIR,
    env: appEnvironment,
    stdio: 'inherit',
  });
  if (result.status !== 0) {
    console.error(`e2e: "uv run ${args.join(' ')}" failed`);
    process.exit(result.status ?? 1);
  }
}

if (!existsSync(resolve(FRONTEND_BUILD_DIR, 'index.html'))) {
  console.error('e2e: no frontend build in frontend/dist: run "pnpm build" first.');
  process.exit(1);
}

runInBackend(['python', '-c', CREATE_DATABASE_IF_MISSING]);
runInBackend(['alembic', 'upgrade', 'head']);

const server: ChildProcess = spawn(
  'uv',
  ['run', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(E2E_APP_PORT)],
  { cwd: BACKEND_DIR, env: appEnvironment, stdio: 'inherit' },
);

for (const signal of ['SIGINT', 'SIGTERM'] as const) {
  process.on(signal, () => server.kill(signal));
}
server.on('exit', (code) => process.exit(code ?? 0));
