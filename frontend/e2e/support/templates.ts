import { expect, type Page } from '@playwright/test';

export async function createTemplate(page: Page, name: string, tileTexts: string[]): Promise<void> {
  await page.goto('/templates');
  await page.getByRole('button', { name: 'Nouveau modèle' }).click();
  await page.getByRole('dialog').getByRole('textbox', { name: 'Nom' }).fill(name);
  await page.getByRole('dialog').getByRole('button', { name: 'Créer' }).click();
  await expect(page.getByRole('heading', { level: 1, name })).toBeVisible();

  const newTileText = page.getByLabel('Texte de la nouvelle tuile', { exact: true });
  for (const text of tileTexts) {
    await newTileText.fill(text);
    await page.getByRole('button', { name: 'Ajouter la tuile' }).click();
    await expect(page.getByRole('textbox', { name: /^Texte de la tuile \d+$/ }).last()).toHaveValue(
      text,
    );
  }
}
