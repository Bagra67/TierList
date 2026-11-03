import { readFileSync } from 'node:fs';

const REPOSITORY_ROOT_FROM_FRONTEND: string = '..';

export function readRepositoryFile(pathFromRepositoryRoot: string): string {
  return readFileSync(`${REPOSITORY_ROOT_FROM_FRONTEND}/${pathFromRepositoryRoot}`, 'utf8');
}
