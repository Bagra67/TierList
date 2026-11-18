import { spawn, type ChildProcess } from 'node:child_process';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';

import { E2E_APP_PORT } from './support/app.ts';
import {
  appEnvironment,
  BACKEND_DIR,
  FRONTEND_BUILD_DIR,
  runInBackend,
} from './support/backend.ts';

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
