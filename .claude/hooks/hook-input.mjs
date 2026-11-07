import { readFileSync } from 'node:fs';
import path from 'node:path';

const STDIN_FILE_DESCRIPTOR = 0;

export function readEditedFile() {
  const hookInput = JSON.parse(readFileSync(STDIN_FILE_DESCRIPTOR, 'utf8'));
  const projectDir = process.env.CLAUDE_PROJECT_DIR ?? hookInput.cwd;
  const absolutePath = hookInput.tool_input?.file_path ?? hookInput.tool_input?.notebook_path;
  if (!absolutePath) {
    return null;
  }
  const projectRelativePath = path.relative(projectDir, absolutePath).split(path.sep).join('/');
  return { projectDir, projectRelativePath };
}

export function blockWithFeedback(message) {
  process.stderr.write(`${message}\n`);
  process.exit(2);
}
