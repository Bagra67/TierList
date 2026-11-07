import { expect, test, type Page } from '@playwright/test';

import { grantSuperAdmin, signUp, type TestAccount } from './support/accounts.ts';
import { createTemplate } from './support/templates.ts';

const PHONE_VIEWPORT = { width: 375, height: 800 } as const;

test.use({ viewport: PHONE_VIEWPORT });

async function expectNoHorizontalScroll(page: Page): Promise<void> {
  await expect
    .poll(
      () =>
        page.evaluate(
          () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
        ),
      { message: `horizontal scroll on ${page.url()}` },
    )
    .toBeLessThanOrEqual(0);
}

test('shows the main pages on a phone without horizontal scroll', async ({ page }) => {
  const account: TestAccount = await signUp(page, 'Maëlys');
  await expectNoHorizontalScroll(page);

  await createTemplate(page, 'Petits-déjeuners', ['Croissant', 'Pain au chocolat']);
  await expectNoHorizontalScroll(page);

  await page.goto('/templates');
  await expect(page.getByRole('link', { name: 'Petits-déjeuners' })).toBeVisible();
  await expectNoHorizontalScroll(page);

  await page.getByRole('button', { name: 'Créer une salle avec Petits-déjeuners' }).click();
  await expect(page.getByRole('heading', { name: /^Salle [A-Z0-9]{6}$/ })).toBeVisible();
  await expectNoHorizontalScroll(page);

  grantSuperAdmin(account);
  for (const path of [
    '/moderation/reports',
    '/moderation/uploads',
    '/moderation/accounts',
    '/moderation/log',
  ]) {
    await page.goto(path);
    await expect(page.getByRole('navigation', { name: 'Espace de modération' })).toBeVisible();
    await expectNoHorizontalScroll(page);
  }
});
