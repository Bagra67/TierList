import { spawnSync } from 'node:child_process';
import path from 'node:path';

import { blockWithFeedback, readEditedFile } from './hook-input.mjs';

const PYTHON_FILE = /^backend\/.+\.py$/;
const FRONTEND_SCRIPT_FILE = /^frontend\/(?!node_modules\/|dist\/).+\.(ts|tsx|js|mjs)$/;
const PRETTIER_ONLY_FILE = /^(frontend\/(?!node_modules\/|dist\/)|docs\/).+\.(json|css|md|html)$/;
const ESLINT_BIN = 'node_modules/eslint/bin/eslint.js';
const PRETTIER_BIN = 'node_modules/prettier/bin/prettier.cjs';

function run(command, args, cwd) {
  const processResult = spawnSync(command, args, { cwd, encoding: 'utf8' });
  if (processResult.error) {
    blockWithFeedback(`Could not run ${command}: ${processResult.error.message}`);
  }
  return {
    succeeded: processResult.status === 0,
    output: `${processResult.stdout}${processResult.stderr}`.trim(),
  };
}

function runOrReport(toolName, command, args, cwd) {
  const { succeeded, output } = run(command, args, cwd);
  if (!succeeded) {
    blockWithFeedback(`${toolName} reported problems it could not fix:\n${output}`);
  }
}

function formatPython(projectDir, projectRelativePath) {
  const backendDir = path.join(projectDir, 'backend');
  const backendRelativePath = projectRelativePath.slice('backend/'.length);
  runOrReport(
    'ruff check',
    'uv',
    ['run', 'ruff', 'check', '--fix', '--quiet', backendRelativePath],
    backendDir,
  );
  runOrReport(
    'ruff format',
    'uv',
    ['run', 'ruff', 'format', '--quiet', backendRelativePath],
    backendDir,
  );
}

function runPrettier(frontendDir, frontendRelativePath) {
  runOrReport(
    'prettier',
    process.execPath,
    [
      PRETTIER_BIN,
      '--config',
      '.prettierrc',
      '--write',
      '--log-level',
      'warn',
      frontendRelativePath,
    ],
    frontendDir,
  );
}

function formatFrontendScript(frontendDir, frontendRelativePath) {
  runOrReport('eslint', process.execPath, [ESLINT_BIN, '--fix', frontendRelativePath], frontendDir);
  runPrettier(frontendDir, frontendRelativePath);
}

const editedFile = readEditedFile();
if (editedFile) {
  const { projectDir, projectRelativePath } = editedFile;
  const frontendDir = path.join(projectDir, 'frontend');
  const frontendRelativePath = path.posix.relative('frontend', projectRelativePath);
  if (PYTHON_FILE.test(projectRelativePath)) {
    formatPython(projectDir, projectRelativePath);
  } else if (FRONTEND_SCRIPT_FILE.test(projectRelativePath)) {
    formatFrontendScript(frontendDir, frontendRelativePath);
  } else if (PRETTIER_ONLY_FILE.test(projectRelativePath)) {
    runPrettier(frontendDir, frontendRelativePath);
  }
}
