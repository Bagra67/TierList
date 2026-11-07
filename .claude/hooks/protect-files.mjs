import { blockWithFeedback, readEditedFile } from './hook-input.mjs';

const PROTECTED_FILES = new Map([
  [
    'backend/openapi.json',
    'Generated file: run `uv run python scripts/export_openapi.py` in backend/ (or /api-sync).',
  ],
  [
    'frontend/src/api/schema.d.ts',
    'Generated file: run `pnpm gen:api` in frontend/ (or /api-sync).',
  ],
  ['backend/uv.lock', 'Managed by uv: use `uv add`, `uv remove` or `uv lock` in backend/.'],
  [
    'frontend/pnpm-lock.yaml',
    'Managed by pnpm: use `pnpm add`, `pnpm remove` or `pnpm install` in frontend/.',
  ],
]);
const ENV_FILE = /(^|\/)\.env(\.[^/]+)?$/;
const ENV_TEMPLATE_FILE = /(^|\/)\.env\.example$/;

const editedFile = readEditedFile();
if (editedFile) {
  const { projectRelativePath } = editedFile;
  const reason = PROTECTED_FILES.get(projectRelativePath);
  if (reason) {
    blockWithFeedback(`${projectRelativePath} must not be edited by hand. ${reason}`);
  }
  if (ENV_FILE.test(projectRelativePath) && !ENV_TEMPLATE_FILE.test(projectRelativePath)) {
    blockWithFeedback(
      `${projectRelativePath} holds local secrets: ask the user to change it. ` +
        'Document new settings in .env.example instead.',
    );
  }
}
