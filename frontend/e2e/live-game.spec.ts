import { expect, test, type BrowserContext, type Page } from '@playwright/test';

import { signUp } from './support/accounts.ts';
import { dragWithMouse } from './support/drag.ts';
import { createTemplate } from './support/templates.ts';

test('plays a live game between a host and a guest, up to the results', async ({
  page: host,
  browser,
}) => {
  await signUp(host, 'Hugo');
  await createTemplate(host, 'Épices', ['Paprika', 'Cumin']);
  await host.getByRole('button', { name: 'Créer une salle avec Épices' }).click();
  await expect(host).toHaveURL(/\/r\/[A-Z0-9]{6}$/);
  const roomPath: string = new URL(host.url()).pathname;

  const guestContext: BrowserContext = await browser.newContext({ locale: 'fr-FR' });
  const guest: Page = await guestContext.newPage();
  await guest.goto(roomPath);
  await guest.getByRole('textbox', { name: 'Pseudo' }).fill('Lou');
  await guest.getByRole('button', { name: 'Rejoindre en invité' }).click();
  await expect(host.getByText('Lou', { exact: true })).toBeVisible();

  await host.getByRole('button', { name: 'Lancer la partie' }).click();
  await expect(guest.getByText('Élément 1 sur 2')).toBeVisible();

  await dragWithMouse(
    host,
    host.getByRole('button', { name: 'Glisser dans un tier : Paprika' }),
    host.getByRole('list', { name: 'S', exact: true }),
  );
  await guest.getByRole('button', { name: /^Placer dans B/ }).click();
  await expect(host.getByText('Placé 2 / 2 connectés')).toBeVisible();
  await expect(host.getByRole('list', { name: 'S', exact: true })).toContainText('Paprika');

  await host.getByRole('button', { name: 'Élément suivant' }).click();
  await expect(guest.getByText('Élément 2 sur 2')).toBeVisible();
  await host.getByRole('button', { name: /^Placer dans A/ }).click();
  await host.getByRole('button', { name: 'Élément suivant' }).click();

  await expect(guest.getByRole('heading', { name: 'Retouches finales' })).toBeVisible();
  const missedItems = guest.getByRole('region', { name: 'Éléments manqués' });
  await expect(missedItems).toContainText('Cumin');
  await guest.getByRole('button', { name: 'Choisir Cumin' }).click();
  await guest.getByRole('button', { name: 'Déplacer Cumin à la fin de C' }).click();
  await expect(missedItems).toContainText('Aucun : tout est placé.');

  await host.getByRole('button', { name: 'Terminer maintenant' }).click();
  const endDialog = host.getByRole('dialog', { name: 'Terminer les retouches ?' });
  await expect(endDialog).toBeVisible();
  await host.keyboard.press('Escape');
  await expect(endDialog).toBeHidden();
  await host.getByRole('button', { name: 'Terminer maintenant' }).click();
  await endDialog.getByRole('button', { name: 'Terminer', exact: true }).click();

  await host.getByRole('link', { name: 'Voir les résultats' }).click();
  await expect(host.getByRole('heading', { name: 'Résultats : Épices' })).toBeVisible();
  await host.getByRole('tab', { name: 'Global' }).click();
  const overall = host.getByRole('tabpanel');
  await expect(overall).toContainText('Paprika');
  await expect(overall).toContainText('Cumin');
  await host.getByRole('tab', { name: 'Par joueur' }).click();
  await expect(host.getByRole('tabpanel')).toContainText('Hugo');

  await guestContext.close();
});
