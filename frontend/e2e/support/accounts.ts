import { randomUUID } from 'node:crypto';

export interface TestAccount {
  displayName: string;
  email: string;
  password: string;
}

export function newAccount(displayName: string): TestAccount {
  return {
    displayName,
    email: `e2e-${randomUUID()}@e2e.example.com`,
    password: `e2e-password-${randomUUID()}`,
  };
}
