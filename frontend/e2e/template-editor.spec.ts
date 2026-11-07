import { expect, test } from '@playwright/test';

import { signUp } from './support/accounts.ts';
import { dragWithMouse } from './support/drag.ts';
import { createTemplate } from './support/templates.ts';

const ONE_PIXEL_PNG: Buffer = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
  'base64',
);

test('builds a template with an image and reordered tiers, kept after a reload', async ({
  page,
}) => {
  await signUp(page, 'Inès');
  await createTemplate(page, 'Épices', ['Paprika', 'Cumin']);

  const chooser = page.waitForEvent('filechooser');
  await page.getByRole('button', { name: 'Ajouter une image à Paprika' }).click();
  await (
    await chooser
  ).setFiles({
    name: 'paprika.png',
    mimeType: 'image/png',
    buffer: ONE_PIXEL_PNG,
  });
  await expect(page.getByRole('button', { name: "Remplacer l'image de Paprika" })).toBeVisible();

  await dragWithMouse(
    page,
    page.getByRole('button', { name: 'Déplacer S' }),
    page.getByRole('button', { name: 'Déplacer B' }),
  );
  await expect(page.getByRole('textbox', { name: 'Nom du tier 3' })).toHaveValue('S');
  await expect(page.getByRole('button', { name: 'Monter S' })).toBeEnabled();

  await page.reload();
  await expect(page.getByRole('textbox', { name: 'Nom du tier 1' })).toHaveValue('A');
  await expect(page.getByRole('textbox', { name: 'Nom du tier 2' })).toHaveValue('B');
  await expect(page.getByRole('textbox', { name: 'Nom du tier 3' })).toHaveValue('S');
  await expect(page.getByRole('textbox', { name: 'Texte de la tuile 1' })).toHaveValue('Paprika');
  await expect(page.getByRole('textbox', { name: 'Texte de la tuile 2' })).toHaveValue('Cumin');
  await expect(page.getByRole('button', { name: "Remplacer l'image de Paprika" })).toBeVisible();
  const paprikaImage = page
    .getByRole('button', { name: "Remplacer l'image de Paprika" })
    .locator('img');
  await expect(paprikaImage).toHaveJSProperty('complete', true);
  expect(
    await paprikaImage.evaluate((image: HTMLImageElement) => image.naturalWidth),
  ).toBeGreaterThan(0);
});
