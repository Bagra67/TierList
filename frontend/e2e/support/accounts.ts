import { randomUUID } from 'node:crypto';

import { expect, type Page } from '@playwright/test';

import { runInBackend } from './backend.ts';

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

export async function signUp(page: Page, displayName: string): Promise<TestAccount> {
  const account: TestAccount = newAccount(displayName);
  await page.goto('/register');
  await page.getByRole('textbox', { name: 'Nom affiché' }).fill(account.displayName);
  await page.getByRole('textbox', { name: 'E-mail' }).fill(account.email);
  await page.getByLabel('Mot de passe').fill(account.password);
  await page.getByRole('button', { name: 'Créer mon compte' }).click();
  await expect(
    page.getByRole('heading', { name: `Prêt pour une partie, ${displayName} ?` }),
  ).toBeVisible();
  return account;
}

export function grantSuperAdmin(account: TestAccount): void {
  runInBackend(['python', 'scripts/set_super_admin.py', account.email]);
}
