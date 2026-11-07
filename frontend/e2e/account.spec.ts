import { expect, test } from '@playwright/test';

import { newAccount, type TestAccount } from './support/accounts.ts';
import { linkSentTo } from './support/mailpit.ts';

test('registers, confirms the email, signs out and in, and keeps the session after a reload', async ({
  page,
  request,
}) => {
  const account: TestAccount = newAccount('Camille');

  await page.goto('/register');
  await page.getByRole('textbox', { name: 'Nom affiché' }).fill(account.displayName);
  await page.getByRole('textbox', { name: 'E-mail' }).fill(account.email);
  await page.getByLabel('Mot de passe').fill(account.password);
  await page.getByRole('button', { name: 'Créer mon compte' }).click();

  await expect(
    page.getByRole('heading', { name: `Prêt pour une partie, Camille ?` }),
  ).toBeVisible();
  await expect(page.getByText(`un lien a été envoyé à ${account.email}`)).toBeVisible();

  await page.goto(await linkSentTo(request, account.email, '/verify-email'));
  await page.getByRole('button', { name: 'Confirmer mon adresse' }).click();
  await expect(page.getByText('Votre adresse e-mail est confirmée.')).toBeVisible();

  await page.goto('/');
  await expect(page.getByText(`un lien a été envoyé à ${account.email}`)).toBeHidden();

  await page.getByRole('button', { name: 'Se déconnecter' }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.getByRole('textbox', { name: 'E-mail' }).fill(account.email);
  await page.getByLabel('Mot de passe').fill(account.password);
  await page.getByRole('button', { name: 'Se connecter' }).click();
  await expect(
    page.getByRole('heading', { name: 'Prêt pour une partie, Camille ?' }),
  ).toBeVisible();

  await page.reload();
  await expect(
    page.getByRole('heading', { name: 'Prêt pour une partie, Camille ?' }),
  ).toBeVisible();

  await page.getByRole('button', { name: 'Se déconnecter' }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.goto('/templates');
  await expect(page).toHaveURL(/\/login$/);
});

test('refuses a wrong password without revealing more', async ({ page }) => {
  await page.goto('/login');
  await page.getByRole('textbox', { name: 'E-mail' }).fill('nobody@e2e.example.com');
  await page.getByLabel('Mot de passe').fill('not-the-right-password');
  await page.getByRole('button', { name: 'Se connecter' }).click();

  await expect(page.getByRole('alert')).toHaveText('E-mail ou mot de passe incorrect');
});
